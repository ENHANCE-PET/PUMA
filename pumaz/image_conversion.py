#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------------------------------------------------------
# Author: Lalith Kumar Shiyam Sundar | Sebastian Gutschmayer
#
# Institution: Medical University of Vienna
# Research Group: Quantitative Imaging and Medical Physics (QIMP) Team
# Date: 07.07.2023
# Version: 1.0.0
#
# Description:
# This module handles image conversion for the pumaz.
#
# Usage:
# The functions in this module can be imported and used in other modules within the pumaz to perform image conversion.
#
# ----------------------------------------------------------------------------------------------------------------------

import contextlib
import io
import os
import re
import unicodedata
from typing import Dict, Optional

import SimpleITK
import dicom2nifti
import pydicom
from nifti2dicom import converter
from pumaz import constants
from pumaz import file_utilities
from pumaz import input_validation
from rich.console import Console
from pumaz.display import themed_progress

console = Console()


def _split_nii_extension(filename: str) -> tuple[str, str]:
    """Split NIfTI filenames while preserving .nii.gz as a single extension."""
    if filename.endswith(".nii.gz"):
        return filename[:-7], ".nii.gz"
    stem, ext = os.path.splitext(filename)
    return stem, ext


def _directory_has_dicom_files(directory: str) -> bool:
    """Check whether a directory contains at least one DICOM file."""
    try:
        entries = os.listdir(directory)
    except OSError:
        return False
    for name in entries:
        if name.startswith("."):
            continue
        full_path = os.path.join(directory, name)
        if os.path.isfile(full_path) and is_dicom_file(full_path):
            return True
    return False


def _new_nifti_files(output_dir: str, before_files: set[str]) -> list[str]:
    """Return newly created NIfTI filenames in output_dir compared to before_files."""
    try:
        after_files = set(os.listdir(output_dir))
    except OSError:
        return []
    return [f for f in after_files - before_files if f.endswith((".nii", ".nii.gz"))]



def convert_dicomdir_series(exam_dir: str, destination_root: str) -> bool:
    """Convert CT/PT series for a single exam directory that contains a DICOMDIR."""
    tracer_name = os.path.basename(os.path.normpath(destination_root))
    converted = False

    for candidate in sorted(os.listdir(exam_dir)):
        image_dir = os.path.join(exam_dir, candidate)
        if not os.path.isdir(image_dir) or candidate.upper() == "DICOMDIR":
            continue

        dicom_file = find_first_dicom(image_dir)
        if not dicom_file:
            continue

        modality = getattr(pydicom.dcmread(dicom_file, stop_before_pixels=True), "Modality", "").upper()
        if modality not in {"PT", "CT"}:
            continue

        existing = [
            f for f in os.listdir(destination_root)
            if f.startswith(f"{modality}_") and f.endswith((".nii", ".nii.gz"))
        ]
        if existing:
            continue

        before_conversion = set(os.listdir(destination_root))
        dcm2niix(image_dir, destination_root)
        dicom_lookup = create_dicom_lookup(image_dir)

        for nifti_file in os.listdir(destination_root):
            if nifti_file in before_conversion:
                continue
            if not nifti_file.endswith((".nii", ".nii.gz")):
                continue
            if nifti_file.startswith(("PT_", "CT_")):
                continue

            src_path = os.path.join(destination_root, nifti_file)
            modality_for_file = _modality_from_lookup(nifti_file, dicom_lookup)
            if modality_for_file not in {"PT", "CT"}:
                modality_for_file = modality
            rename_dicom_output(src_path, modality_for_file, tracer_name, destination_root)
            converted = True

    return converted


def rename_dicom_output(src_path: str, modality: str, tracer_name: str, destination_root: str) -> None:
    """Rename the converted NIFTI to match PUMA naming expectations."""
    extension = ".nii.gz" if src_path.endswith(".nii.gz") else ".nii"
    clean_tracer = remove_accents(tracer_name)
    base_name = f"{modality}_{clean_tracer}{extension}"
    destination = os.path.join(destination_root, base_name)
    counter = 1
    while os.path.exists(destination):
        base_name = f"{modality}_{clean_tracer}_{counter}{extension}"
        destination = os.path.join(destination_root, base_name)
        counter += 1

    os.replace(src_path, destination)

    # Move accompanying JSON if it sits with the source NIFTI
    src_json = os.path.splitext(src_path)[0] + ".json"
    if os.path.exists(src_json):
        dest_json = os.path.splitext(destination)[0] + ".json"
        os.replace(src_json, dest_json)


def _modality_from_lookup(nifti_filename: str, dicom_lookup: dict) -> Optional[str]:
    """Resolve the modality for a converted NIfTI file using a DICOM lookup map."""
    base = os.path.splitext(nifti_filename)[0]
    candidates = (
        nifti_filename,
        base + ".nii",
        base + ".nii.gz",
    )
    for candidate in candidates:
        modality = dicom_lookup.get(candidate)
        if modality:
            return modality

    for key, value in dicom_lookup.items():
        key_base = os.path.splitext(key)[0]
        if key_base == base or key_base.startswith(base) or base.startswith(key_base):
            return value

    return None


def find_first_dicom(directory: str) -> Optional[str]:
    """Return the first DICOM file found within directory (recursively)."""
    for root, _, files in os.walk(directory):
        for filename in sorted(files):
            if filename.startswith("."):
                continue
            full_path = os.path.join(root, filename)
            if is_dicom_file(full_path):
                return full_path
    return None


def non_nifti_to_nifti(input_path: str, output_directory: str = None) -> None:
    """
    Converts any image format known to ITK to NIFTI.

    :param input_path: The directory or filename to convert to NIFTI.
    :type input_path: str
    :param output_directory: The optional output directory to write the image to.
    :type output_directory: str, optional
    :return: None
    :rtype: None
    :raises: None

    This function converts any image format known to ITK to NIFTI. If the input path is a directory, it either parses a
    DICOMDIR (if present) or runs the `dcm2niix` command to convert the images to NIFTI. If the input path is a file, it
    reads the image using SimpleITK and writes it to a NIFTI file. If an output directory is not specified, the NIFTI
    file is written to the same directory as the input file.

    :Example:
        >>> non_nifti_to_nifti('/path/to/input/image.jpg', '/path/to/output/directory')
    """

    if not os.path.exists(input_path):
        print(f"Input path {input_path} does not exist.")
        return

    # Processing a directory
    if os.path.isdir(input_path):
        dicomdir_path = os.path.join(input_path, "DICOMDIR")
        if os.path.isfile(dicomdir_path):
            try:
                destination_root = os.path.dirname(input_path)
                if convert_dicomdir_series(input_path, destination_root):
                    return
            except Exception as exc:  # fallback to legacy behaviour on failure
                console.print(
                    f"  [yellow]DICOMDIR parsing failed for {input_path}: {exc}. Falling back to directory scan.[/yellow]"
                )

        destination_root = output_directory or os.path.dirname(input_path)
        if _directory_has_dicom_files(input_path):
            dicom_info = create_dicom_lookup(input_path)
            before_conversion = set(os.listdir(destination_root))
            nifti_dir = dcm2niix(input_path, destination_root)
            rename_nifti_files(
                nifti_dir,
                dicom_info,
                new_files=_new_nifti_files(nifti_dir, before_conversion),
            )
            return

        dicom_modalities = input_validation.identify_medical_image_data(input_path)
        if not dicom_modalities:
            return

        for modality in constants.MODALITIES:
            series_dir = dicom_modalities.get(modality)
            if not series_dir:
                continue
            before_conversion = set(os.listdir(destination_root))
            dcm2niix(series_dir, destination_root)
            new_files = _new_nifti_files(destination_root, before_conversion)
            if not new_files:
                continue
            rename_nifti_files(
                destination_root,
                create_dicom_lookup(series_dir),
                new_files=new_files,
                fallback_modality=modality,
            )
        return

    # Processing a file
    if os.path.isfile(input_path):
        # Ignore hidden or already processed files
        _, filename = os.path.split(input_path)
        if filename.startswith('.') or filename.endswith(('.nii.gz', '.nii')):
            return
        else:
            output_image = SimpleITK.ReadImage(input_path)
            output_image_basename = f"{os.path.splitext(filename)[0]}.nii"

    if output_directory is None:
        output_directory = os.path.dirname(input_path)

    output_image_path = os.path.join(output_directory, output_image_basename)
    SimpleITK.WriteImage(output_image, output_image_path)


def standardize_to_nifti(parent_dir: str):
    """
    Converts all images in a parent directory to NIFTI.

    :param parent_dir: The parent directory containing the images to convert.
    :type parent_dir: str
    :return: None
    :rtype: None
    :raises: None

    This function converts all images in a parent directory to NIFTI. It goes through the subdirectories of the parent
    directory and converts any non-NIFTI images to NIFTI using the `non_nifti_to_nifti` function.

    :Example:
        >>> standardize_to_nifti('/path/to/parent/directory')
    """
    # go through the subdirectories
    subjects = os.listdir(parent_dir)
    # get only the directories
    subjects = [subject for subject in subjects if os.path.isdir(os.path.join(parent_dir, subject))]

    with themed_progress(expand=True) as progress:
        task = progress.add_task(" Standardizing subjects...", total=len(subjects))
        for subject in subjects:
            subject_path = os.path.join(parent_dir, subject)
            if os.path.isdir(subject_path):
                images = os.listdir(subject_path)
                for image in images:
                    if os.path.isdir(os.path.join(subject_path, image)):
                        image_path = os.path.join(subject_path, image)
                        non_nifti_to_nifti(image_path)
                    elif os.path.isfile(os.path.join(subject_path, image)):
                        image_path = os.path.join(subject_path, image)
                        non_nifti_to_nifti(image_path)
            else:
                continue
            progress.update(task, advance=1, description=f" Standardizing {subject}...")


def dcm2niix(input_path: str, output_dir: Optional[str] = None) -> str:
    """
    Converts DICOM images into Nifti images using dcm2niix.

    :param input_path: The path to the folder with the DICOM files to convert.
    :type input_path: str
    :return: The path to the folder with the converted Nifti files.
    :rtype: str
    :raises: None

    This function converts DICOM images into Nifti images using the `dicom2nifti` package. It takes the path to the folder
    with the DICOM files as input and returns the path to the folder with the converted Nifti files.

    :Example:
        >>> dcm2niix('/path/to/dicom/folder')
    """
    if output_dir is None:
        output_dir = os.path.dirname(input_path)

    # redirect standard output and standard error to discard output
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        dicom2nifti.convert_directory(input_path, output_dir, compression=False, reorient=True)

    return output_dir


def remove_accents(unicode_filename):
    """
    Removes accents and special characters from a Unicode filename.

    :param unicode_filename: The Unicode filename to clean.
    :type unicode_filename: str
    :return: The cleaned filename.
    :rtype: str
    :raises: None

    This function removes accents and special characters from a Unicode filename. It replaces spaces with underscores,
    normalizes the Unicode string to remove accents, removes any non-word characters, and replaces spaces and hyphens
    with a single hyphen.

    :Example:
        >>> remove_accents('éàï_ö.jpg')
        'eai_o.jpg'
    """
    try:
        unicode_filename = str(unicode_filename).replace(" ", "_")
        cleaned_filename = unicodedata.normalize('NFKD', unicode_filename).encode('ASCII', 'ignore').decode('ASCII')
        cleaned_filename = re.sub(r'[^\w\s-]', '', cleaned_filename.strip().lower())
        cleaned_filename = re.sub(r'[-\s]+', '-', cleaned_filename)
        return cleaned_filename
    except:
        return unicode_filename


def is_dicom_file(filename):
    """
    Checks if a file is a DICOM file.

    :param filename: The filename to check.
    :type filename: str
    :return: True if the file is a DICOM file, False otherwise.
    :rtype: bool
    :raises: None

    This function checks if a file is a DICOM file by attempting to read it using the `pydicom` package. If the file is
    a DICOM file, it returns True. If the file is not a DICOM file, it returns False.

    :Example:
        >>> is_dicom_file('/path/to/dicom/file.dcm')
        True
    """
    try:
        pydicom.dcmread(filename, stop_before_pixels=True)
        return True
    except pydicom.errors.InvalidDicomError:
        return False


def create_dicom_lookup(dicom_dir):
    """
    Create a lookup dictionary from DICOM files.

    :param dicom_dir: The directory where DICOM files are stored.
    :type dicom_dir: str
    :return: A dictionary where the key is the anticipated filename that dicom2nifti will produce and the value is the
             modality of the DICOM series.
    :rtype: dict
    :raises: None

    This function creates a lookup dictionary from DICOM files. It loops over the DICOM files in the specified
    directory, reads each DICOM file using the `pydicom` package, and extracts the necessary information to create a
    filename that `dicom2nifti` will produce. It then stores the modality tag with the anticipated filename in a
    dictionary.

    :Example:
        >>> create_dicom_lookup('/path/to/dicom/folder')
        {'1_T1.nii': 'MR', '2_T2.nii': 'MR', '3_PET.nii': 'PET'}

    """
    # a dictionary to store information from the DICOM files
    dicom_info = {}

    # loop over the DICOM files
    for root, _, filenames in os.walk(dicom_dir):
        for filename in filenames:
            if filename.upper() == "DICOMDIR":
                continue
            full_path = os.path.join(root, filename)
            if os.path.isdir(full_path):
                continue
            if is_dicom_file(full_path):
                # read the DICOM file
                ds = pydicom.dcmread(full_path, stop_before_pixels=True)
                # extract the necessary information
                series_number = ds.SeriesNumber if 'SeriesNumber' in ds else None
                series_description = ds.SeriesDescription if 'SeriesDescription' in ds else None
                sequence_name = ds.SequenceName if 'SequenceName' in ds else None
                protocol_name = ds.ProtocolName if 'ProtocolName' in ds else None
                series_instance_UID = ds.SeriesInstanceUID if 'SeriesInstanceUID' in ds else None
                modality = getattr(ds, "Modality", None)
                if modality is None:
                    continue

                # anticipate the filename dicom2nifti will produce and store the modality tag with it
                if series_number is not None:
                    base_filename = remove_accents(series_number)
                    if series_description is not None:
                        anticipated_filename = f"{base_filename}_{remove_accents(series_description)}.nii"
                    elif sequence_name is not None:
                        anticipated_filename = f"{base_filename}_{remove_accents(sequence_name)}.nii"
                    elif protocol_name is not None:
                        anticipated_filename = f"{base_filename}_{remove_accents(protocol_name)}.nii"
                    else:
                        anticipated_filename = f"{base_filename}.nii"
                else:
                    anticipated_filename = f"{remove_accents(series_instance_UID)}.nii"

                dicom_info[anticipated_filename] = modality

    return dicom_info


def rename_nifti_files(nifti_dir, dicom_info, new_files=None, fallback_modality: Optional[str] = None):
    """
    Rename NIfTI files based on a lookup dictionary.

    :param nifti_dir: The directory where NIfTI files are stored.
    :type nifti_dir: str
    :param dicom_info: A dictionary where the key is the anticipated filename that dicom2nifti will produce and the
                       value is the modality of the DICOM series.
    :type dicom_info: dict
    :param new_files: Optional list of new filenames to consider for renaming.
    :type new_files: list, optional
    :param fallback_modality: Optional modality to use when no lookup entry exists.
    :type fallback_modality: str, optional
    :return: None
    :rtype: None
    :raises: None

    This function renames NIfTI files based on a lookup dictionary. It loops over the NIfTI files in the specified
    directory, gets the corresponding DICOM information from the lookup dictionary, creates a new filename using the
    modality and the original filename, renames the file, and deletes the old name from the dictionary.

    :Example:
        >>> rename_nifti_files('/path/to/nifti/folder', {'1_T1.nii': 'MR', '2_T2.nii': 'MR', '3_PET.nii': 'PET'})
    """
    # loop over the NIfTI files
    filenames = new_files if new_files is not None else os.listdir(nifti_dir)
    for filename in filenames:
        if not filename.endswith((".nii", ".nii.gz")):
            continue

        upper_name = filename.upper()
        if upper_name.startswith(tuple(constants.MODALITIES)):
            continue

        modality = _modality_from_lookup(filename, dicom_info or {})
        if not modality and fallback_modality:
            modality = fallback_modality
        if not modality:
            continue

        modality = modality.upper()
        stem, extension = _split_nii_extension(filename)
        new_filename = f"{modality}_{stem}{extension}"
        destination = os.path.join(nifti_dir, new_filename)
        counter = 1
        while os.path.exists(destination):
            new_filename = f"{modality}_{stem}_{counter}{extension}"
            destination = os.path.join(nifti_dir, new_filename)
            counter += 1

        src_path = os.path.join(nifti_dir, filename)
        os.replace(src_path, destination)

        src_json = os.path.join(nifti_dir, stem + ".json")
        if os.path.exists(src_json):
            dest_stem, _ = _split_nii_extension(new_filename)
            dest_json = os.path.join(nifti_dir, dest_stem + ".json")
            os.replace(src_json, dest_json)


class NiftiToDicomConverter:
    def __init__(self, subject_folder, puma_dir):
        self.subject_folder = subject_folder
        self.puma_dir = puma_dir
        self.reference_img = None
        self.moving_img_dicom_dirs = []
        self.moving_nifti_imgs = []

    def set_reference_image(self, reference_img):
        """Sets the reference image for the conversion process."""
        self.reference_img = reference_img

    def _get_reference_image_info(self):
        """Extracts and prepares reference image information."""
        reference_img_basename = os.path.basename(self.reference_img)
        # Ensure we're splitting by the correct prefix and capturing the expected directory name portion
        reference_img_dirname_parts = reference_img_basename.split('_resampled_')
        if len(reference_img_dirname_parts) > 1:
            reference_img_dirname = reference_img_dirname_parts[0]
        else:
            # Handle cases where the '_resampled_' string is not found
            reference_img_dirname = reference_img_basename

        # Assuming self.subject_folder is the path up to .../PUMA/00-MTIC/
        reference_img_dicom_dir = os.path.join(self.subject_folder, reference_img_dirname)

        return reference_img_dirname, reference_img_dicom_dir

    def _find_moving_images(self, puma_compliant_subject_folders):
        """Identifies and prepares moving images for conversion, ensuring each key is hashable."""
        _, reference_img_dicom_dir = self._get_reference_image_info()
        self.moving_img_dicom_dirs = [d for d in puma_compliant_subject_folders if d != reference_img_dicom_dir]
        self.moving_nifti_imgs = [
            tuple(file_utilities.find_images(os.path.join(self.puma_dir, constants.ALIGNED_PET_FOLDER),
                                             '*' + os.path.basename(m) + '*'))
            for m in self.moving_img_dicom_dirs
        ]

    def convert_to_dicom(self, puma_compliant_subject_folders):
        """Performs the NIfTI to DICOM conversion for all moving images, correctly handling list keys."""
        if not self.reference_img:
            raise ValueError("Reference image not set.")

        reference_img_dirname, reference_img_dicom_dir = self._get_reference_image_info()
        self._find_moving_images(puma_compliant_subject_folders)

        ref_dicom_dir_info = input_validation.identify_modalities(reference_img_dicom_dir)

        # Ensure we are creating a dictionary with hashable keys
        moving_nifti_dicom_dirs = {moving_nifti_img: moving_dicom_dir for moving_nifti_img, moving_dicom_dir in
                                   zip(self.moving_nifti_imgs, self.moving_img_dicom_dirs) if moving_nifti_img}

        for moving_nifti_imgs, moving_dicom_dir in moving_nifti_dicom_dirs.items():
            for moving_nifti_img in moving_nifti_imgs:  # Process each NIfTI image individually
                output_dicom_dir = os.path.join(self.puma_dir, constants.ALIGNED_PET_FOLDER,
                                                os.path.splitext(os.path.basename(moving_nifti_img))[0] +
                                                '_' + constants.DICOM_FOLDER)
                moving_dicom_dir_info = input_validation.identify_modalities(moving_dicom_dir)
                converter.nifti_to_dicom_with_resampling(
                    nifti_image_path=moving_nifti_img,
                    original_dicom_directory=moving_dicom_dir_info.get('PT'),
                    dicom_output_directory=output_dicom_dir,
                    spatial_info_dicom_directory=ref_dicom_dir_info.get('PT'),
                    series_description=constants.DESCRIPTION,
                    verbose=False,
                )

        # Convert MPX images to DICOM

        mpx_img = file_utilities.get_files(
            os.path.join(self.puma_dir, constants.ALIGNED_PET_FOLDER),
            f'{constants.MULTIPLEXED_COMPOSITE_IMAGE}'
        )[0]

        mpx_dicom_dir = os.path.join(self.puma_dir, constants.ALIGNED_PET_FOLDER,
                                     constants.MULTIPLEXED_COMPOSITE_IMAGE + '_' + constants.DICOM_FOLDER)

        converter.write_rgb_dicom_from_nifti(nifti_file_path=mpx_img,
                                             reference_dicom_series=ref_dicom_dir_info.get('PT'),
                                             output_directory=mpx_dicom_dir)

        reference_nifti_img = file_utilities.get_files(
            os.path.join(self.puma_dir, constants.ALIGNED_PET_FOLDER),
            f'*{reference_img_dirname}*'
        )[0]

        console.print(f"🔍 Reference tracer image directory: {reference_img_dicom_dir}. Kindly use the "
                      f"CT from here when overlaying the aligned PT dicom or the MPX images!", style="white")

        self._move_reference_dicom_dir(ref_dicom_dir_info.get('PT'),
                                       os.path.splitext(os.path.basename(reference_nifti_img))[0])

    def _move_reference_dicom_dir(self, reference_img_dicom_dir, reference_img_dirname):
        """Moves the reference DICOM directory to the aligned PET directory."""
        aligned_reference_dir = os.path.join(self.puma_dir, constants.ALIGNED_PET_FOLDER,
                                             reference_img_dirname + '_' + constants.DICOM_FOLDER)
        file_utilities.create_directory(aligned_reference_dir)
        reference_dcm_files = file_utilities.get_files(reference_img_dicom_dir, '*')
        file_utilities.copy_files_to_destination(reference_dcm_files, aligned_reference_dir)
