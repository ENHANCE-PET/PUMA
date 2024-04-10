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

import SimpleITK
import dicom2nifti
import pydicom
from nifti2dicom import converter
from pumaz import constants
from pumaz import file_utilities
from pumaz import input_validation
from rich.console import Console
from rich.progress import Progress

console = Console()


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

    This function converts any image format known to ITK to NIFTI. If the input path is a directory, it creates a DICOM
    lookup and runs the `dcm2niix` command to convert the images to NIFTI. If the input path is a file, it reads the image
    using SimpleITK and writes it to a NIFTI file. If an output directory is not specified, the NIFTI file is written to
    the same directory as the input file.

    :Example:
        >>> non_nifti_to_nifti('/path/to/input/image.jpg', '/path/to/output/directory')
    """

    if not os.path.exists(input_path):
        print(f"Input path {input_path} does not exist.")
        return

    # Processing a directory
    if os.path.isdir(input_path):
        dicom_info = create_dicom_lookup(input_path)
        nifti_dir = dcm2niix(input_path)
        rename_nifti_files(nifti_dir, dicom_info)
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

    with Progress() as progress:
        task = progress.add_task("[white] Standardizing subjects...", total=len(subjects))
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
            progress.update(task, advance=1, description=f"[white] Standardizing {subject}...")


def dcm2niix(input_path: str) -> str:
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
        pydicom.dcmread(filename)
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
    for filename in os.listdir(dicom_dir):
        full_path = os.path.join(dicom_dir, filename)
        if is_dicom_file(full_path):
            # read the DICOM file
            ds = pydicom.dcmread(full_path)

            # extract the necessary information
            series_number = ds.SeriesNumber if 'SeriesNumber' in ds else None
            series_description = ds.SeriesDescription if 'SeriesDescription' in ds else None
            sequence_name = ds.SequenceName if 'SequenceName' in ds else None
            protocol_name = ds.ProtocolName if 'ProtocolName' in ds else None
            series_instance_UID = ds.SeriesInstanceUID if 'SeriesInstanceUID' in ds else None
            modality = ds.Modality

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
                anticipated_filename = f"{remove_accents(series_instance_UID)}.nii"

            dicom_info[anticipated_filename] = modality

    return dicom_info


def rename_nifti_files(nifti_dir, dicom_info):
    """
    Rename NIfTI files based on a lookup dictionary.

    :param nifti_dir: The directory where NIfTI files are stored.
    :type nifti_dir: str
    :param dicom_info: A dictionary where the key is the anticipated filename that dicom2nifti will produce and the
                       value is the modality of the DICOM series.
    :type dicom_info: dict
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
    for filename in os.listdir(nifti_dir):
        if filename.endswith('.nii'):
            # get the corresponding DICOM information
            modality = dicom_info.get(filename, '')
            if modality:  # only if the modality is found in the dicom_info dict
                # create the new filename
                new_filename = f"{modality}_{filename}"

                # rename the file
                os.rename(os.path.join(nifti_dir, filename), os.path.join(nifti_dir, new_filename))

                # delete the old name from the dictionary
                del dicom_info[filename]


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
