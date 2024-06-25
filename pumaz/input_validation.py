#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------------------------------------------------------
# Author: Lalith Kumar Shiyam Sundar | Sebastian Gutschmayer
# Institution: Medical University of Vienna
# Research Group: Quantitative Imaging and Medical Physics (QIMP) Team
# Date: 07.07.2023
# Version: 1.0.0
#
# Description:
# This module performs input validation for the pumaz. It verifies that the inputs provided by the user are valid
# and meets the required specifications.
#
# Usage:
# The functions in this module can be imported and used in other modules within the moosez to perform input validation.
#
# ----------------------------------------------------------------------------------------------------------------------

import logging
import os

import pydicom
from dask import delayed, compute
from pumaz import constants
from pumaz import image_conversion
from rich.console import Console
from rich.progress import Progress, TextColumn, TimeElapsedColumn, SpinnerColumn

console = Console()


def select_puma_compliant_subject_folders(tracer_paths: list) -> list:
    """
    Selects the subjects that have the files that have names that are compliant with the pumaz.
    :param tracer_paths: The path to the list of tracer directories that are present in the subject directory.
    :return: The list of tracer paths that are pumaz compliant.
    """
    # go through each subject in the parent directory
    puma_compliant_subjects = []
    for subject_path in tracer_paths:
        # go through each subject and see if the files have the appropriate modality prefixes
        files = [file for file in os.listdir(subject_path) if file.endswith('.nii') or file.endswith('.nii.gz')]
        anatomical_prefixes = [file.startswith(tag) for tag in constants.ANATOMICAL_MODALITIES for file in files]
        functional_prefixes = [file.startswith(tag) for tag in constants.FUNCTIONAL_MODALITIES for file in files]

        if sum(anatomical_prefixes) == 1 and sum(functional_prefixes) == 1:
            puma_compliant_subjects.append(subject_path)
    console.print(f" Number of puma compliant tracer directories: {len(puma_compliant_subjects)} out of "
                  f"{len(tracer_paths)} ", style="bold magenta")
    logging.info(f" Number of puma compliant tracer directories: {len(puma_compliant_subjects)} out of "
                 f"{len(tracer_paths)}")

    return puma_compliant_subjects


def identify_modalities(directory):
    """
    Identify the modalities in a given directory.

    This function uses the `identify_medical_image_data` function to identify the types of medical imaging data
    present in the specified directory. It displays a progress bar during the operation using the `Progress` class
    from the `rich.progress` module. The function returns a dictionary containing the identified modalities.

    Parameters:
    directory (str): The directory to identify the modalities from.

    Returns:
    dict: A dictionary containing the identified modalities. The keys are the modality tags and the values are
    the topmost directory paths for each modality.

    Example:
    >>> directory = "/path/to/directory"
    >>> modalities = identify_modalities(directory)
    >>> print(modalities)
    {'PT': '/path/to/directory/PT', 'CT': '/path/to/directory/CT'}
    """
    with Progress(
            SpinnerColumn(),  # Spinner column to show the spinner
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            transient=True,  # Hides the progress bar after completion
    ) as progress:
        task = progress.add_task(" Identifying modalities • Time elapsed:", total=None)

        # Call your function here
        data_info = identify_medical_image_data(directory)

        progress.update(task, completed=100, description="[green] Done:tick:")

    return data_info


def process_file(file_path: str):
    """
    Process a single DICOM file to extract its modality.

    This function reads a DICOM file and extracts the 'Modality' tag from the file's metadata.
    It returns a tuple containing the modality and the directory of the file.

    Parameters:
    file_path (str): The path to the DICOM file to be processed.

    Returns:
    tuple: A tuple containing the modality (str) and the directory of the file (str).

    Raises:
    ValueError: If the 'Modality' tag is not found in the DICOM file or if there is a problem reading the DICOM file.
    """
    try:
        with open(file_path, 'rb') as dcm_file:
            dicom_data = pydicom.filereader.read_partial(dcm_file, specific_tags=['Modality'])
        modality = dicom_data.get('Modality', None)
        if modality:
            return modality, os.path.dirname(file_path)
        else:
            raise ValueError("Modality tag not found in DICOM file.")
    except Exception as e:
        raise ValueError(f"Error reading DICOM file {file_path}: {e}")


def identify_medical_image_data(directory):
    """
    Identify the type of medical imaging data in the given directory and store the topmost directory for each modality.

    This function walks through the given directory and its subdirectories to identify the type of medical imaging data
    present. It checks for the presence of 'PT' and 'CT' directories and adds their paths to the result dictionary.
    If these directories are not found, it processes each file in the directory and its subdirectories to identify the
    modality. The function uses Dask to process the files in parallel. The result is a dictionary with modality tags as
    keys and the topmost directory path for each modality as values.

    Args:
        directory (str): The path to the directory to be checked.

    Returns:
        dict: A dictionary with modality tags as keys and the topmost directory path as values.

    Raises:
        ValueError: If there is a problem reading the DICOM file.
    """
    result = {}
    pt_path = os.path.join(directory, 'PT')
    ct_path = os.path.join(directory, 'CT')

    # Check for the presence of 'PT' and 'CT' directories
    if os.path.isdir(pt_path) and os.path.isdir(ct_path):
        result['PT'] = pt_path
        result['CT'] = ct_path
    else:
        tasks = []
        # get only the subdirectories
        subdirs = [subdir for subdir in os.listdir(directory) if os.path.isdir(os.path.join(directory, subdir))]
        # Walk through the directory and its subdirectories
        for subdir in subdirs:
            # get all the file paths in the subdirectory and is_dicom_file
            files = [file for file in os.listdir(os.path.join(directory, subdir)) if
                     os.path.isfile(os.path.join(directory, subdir, file)) and
                     image_conversion.is_dicom_file(os.path.join(directory, subdir, file))]
            for file in files:
                file_path = os.path.join(directory, subdir, file)
                tasks.append(delayed(process_file)(file_path))

        # Use Dask to process the files in parallel
        results = compute(*tasks)
        for modality, subdir in results:
            # Add the modality and the topmost directory path to the result dictionary
            if modality and modality not in result:
                result[modality] = subdir

    return result
