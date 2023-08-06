#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------------------------------------------------------
# Author: Lalith Kumar Shiyam Sundar | Sebastian Gutschmayer
# Institution: Medical University of Vienna
# Research Group: Quantitative Imaging and Medical Physics (QIMP) Team
# Date: 07.07.2023
# Version: 1.0.0
#
# Module: image_conversion
#
# Description:
# The `image_conversion` module is PUMA-Z's trusted bridge for converting between medical image formats. 
# Leveraging robust libraries like SimpleITK and dicom2nifti, this module ensures that no matter the original 
# format, the data can be converted to a universally accepted NIFTI format. Whether working with individual 
# images or an entire directory of medical scans, the utilities within this module guarantee a smooth and 
# efficient transformation process.
#
# Usage:
# A powerhouse in its own right, the functions in this module can be summoned across PUMA-Z to perform 
# versatile image conversions. With the ability to handle DICOM, ITK-known formats, and more, these utilities 
# offer an all-encompassing solution to the challenges posed by diverse medical image types.
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
from rich.progress import Progress


def non_nifti_to_nifti(input_path: str, output_directory: str = None) -> None:
    """
    Converts an image format known to ITK to the NIFTI format.

    Parameters:
    - `input_path` (str): Path to the input file or directory containing the image(s) to be converted.
    - `output_directory` (str, optional): The directory where the converted image will be saved. If None, the image
      will be saved in the same location as the input.

    Note:
    - If the input_path is a directory, the function will create a lookup for DICOMs and rename NIFTI files accordingly.
    - If the input_path is a file, it will be converted directly to the NIFTI format.

    Raises:
    - FileNotFoundError: If the input path does not exist.
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
    Converts all images within a specified directory (and its sub-directories) to the NIFTI format.

    Parameters:
    - `parent_dir` (str): The parent directory containing the images or subdirectories with images to be converted.

    Note:
    - This function traverses through all the subdirectories of the provided parent directory and converts all images 
      found to the NIFTI format.
    """

    # go through the subdirectories
    subjects = os.listdir(parent_dir)
    # get only the directories
    subjects = [subject for subject in subjects if os.path.isdir(os.path.join(parent_dir, subject))]

    with Progress() as progress:
        task = progress.add_task("[white] Processing subjects...", total=len(subjects))
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
            progress.update(task, advance=1, description=f"[white] Processing {subject}...")


def dcm2niix(input_path: str) -> str:
    """
    Converts DICOM images to NIFTI images using the dicom2nifti utility.

    Parameters:
    - `input_path` (str): Path to the folder containing the DICOM files.

    Returns:
    - `str`: Path to the folder containing the converted NIFTI files.

    Note:
    - This function utilizes the dcm2niix utility for conversion. Ensure that dcm2niix is properly installed and set up 
      in your environment.
    """

    output_dir = os.path.dirname(input_path)

    # redirect standard output and standard error to discard output
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        dicom2nifti.convert_directory(input_path, output_dir, compression=False, reorient=True)

    return output_dir


def remove_accents(unicode_filename):
    """
    Removes accents from a given string and returns a cleaned version of the filename.

    Parameters:
    - `unicode_filename` (str): The filename to be cleaned.

    Returns:
    - `str`: The cleaned filename without any accents and special characters.

    Note:
    - If any exception occurs during the processing, the original filename will be returned.
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
    Determines if the provided file is a valid DICOM file.

    Parameters:
    - `filename` (str): Path to the file to be checked.

    Returns:
    - `bool`: True if the file is a valid DICOM file, False otherwise.
    """

    try:
        pydicom.dcmread(filename)
        return True
    except pydicom.errors.InvalidDicomError:
        return False


def create_dicom_lookup(dicom_dir):
    """
    Generates a lookup dictionary from DICOM files.

    Parameters:
    - `dicom_dir` (str): Directory containing the DICOM files.

    Returns:
    - `dict`: A dictionary where the key is the anticipated filename produced by dicom2nifti and the value is the modality 
      of the DICOM series.

    Note:
    - This function is particularly useful when renaming NIFTI files post-conversion.
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
            if ds.Modality == 'PT':
                modality = 'PET'
            else:
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
    Renames NIFTI files based on the provided lookup dictionary.

    Parameters:
    - `nifti_dir` (str): Directory containing the NIFTI files.
    - `dicom_info` (dict): A dictionary where the key is the anticipated filename that dicom2nifti will produce and the 
      value is the modality of the DICOM series.

    Note:
    - Only files with a corresponding modality in the dicom_info dictionary will be renamed. Others will be left unchanged.
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
