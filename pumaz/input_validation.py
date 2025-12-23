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
from typing import List, Sequence, Tuple

import pydicom
from pumaz import constants
from rich.console import Console
from rich.progress import Progress, TextColumn, TimeElapsedColumn, SpinnerColumn

console = Console()


class MissingModalitiesError(RuntimeError):
    """Raised when a tracer directory lacks required CT/PT modalities."""

    def __init__(self, failures: Sequence[Tuple[str, Sequence[str]]]):
        self.failures: List[Tuple[str, Sequence[str]]] = list(failures)
        details = "\n".join(f"- {path}: {', '.join(reasons)}" for path, reasons in self.failures)
        message = (
            "Missing or invalid modality requirements detected for the following tracer directories:\n"
            f"{details}"
        )
        super().__init__(message)


def select_puma_compliant_subject_folders(tracer_paths: list) -> list:
    """
    Selects the subjects that have the files that have names that are compliant with the pumaz.
    :param tracer_paths: The path to the list of tracer directories that are present in the subject directory.
    :return: The list of tracer paths that are pumaz compliant.
    """
    # go through each subject in the parent directory
    puma_compliant_subjects: list[str] = []
    failures: list[Tuple[str, list[str]]] = []
    for subject_path in tracer_paths:
        # go through each subject and see if the files have the appropriate modality prefixes
        files = [file for file in os.listdir(subject_path) if file.endswith('.nii') or file.endswith('.nii.gz')]
        try:
            dicom_modalities = identify_medical_image_data(subject_path)
        except Exception:  # pragma: no cover - defensive, diagnostic only
            dicom_modalities = {}

        ct_count = sum(
            file.upper().startswith(tag) for tag in constants.ANATOMICAL_MODALITIES for file in files
        )
        pt_count = sum(
            file.upper().startswith(tag) for tag in constants.FUNCTIONAL_MODALITIES for file in files
        )

        ct_present = bool(ct_count) or any(tag in dicom_modalities for tag in constants.ANATOMICAL_MODALITIES)
        pt_present = bool(pt_count) or any(tag in dicom_modalities for tag in constants.FUNCTIONAL_MODALITIES)

        issues: list[str] = []

        if not ct_present:
            issues.append("missing CT volume")
        elif ct_count > 1:
            issues.append(f"found {ct_count} CT volumes")

        if not pt_present:
            issues.append("missing PT volume")
        elif pt_count > 1:
            issues.append(f"found {pt_count} PT volumes")

        if issues:
            failures.append((subject_path, issues))
        else:
            puma_compliant_subjects.append(subject_path)
    console.print(
        f" Number of PUMA-compliant tracer directories: {len(puma_compliant_subjects)} out of {len(tracer_paths)}",
        style=constants.PUMAZ_COLORS["accent"],
    )
    logging.info(f" Number of puma compliant tracer directories: {len(puma_compliant_subjects)} out of "
                 f"{len(tracer_paths)}")

    if failures:
        raise MissingModalitiesError(failures)

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
            SpinnerColumn(style=constants.PUMAZ_COLORS["accent"]),
            TextColumn(f"[{constants.PUMAZ_COLORS['accent']}]{{task.description}}"),
            TimeElapsedColumn(),
            transient=True,
    ) as progress:
        task = progress.add_task("Identifying modalities • Time elapsed:", total=None)

        # Call your function here
        data_info = identify_medical_image_data(directory)

        progress.update(task, completed=100, description=f"[{constants.PUMAZ_COLORS['success']}]Done ✔")

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
        dicom_data = pydicom.dcmread(file_path, stop_before_pixels=True, specific_tags=['Modality'])
        modality = getattr(dicom_data, 'Modality', None)
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
    modality. The function scans subdirectories recursively and returns a dictionary with modality tags as keys and the
    directory paths where the first matching series was detected.

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
        return result

    for root, dirnames, filenames in os.walk(directory):
        dirnames[:] = [name for name in dirnames if not name.startswith('.')]
        for filename in filenames:
            if filename.startswith('.'):
                continue
            lower_name = filename.lower()
            if lower_name.endswith(('.nii', '.nii.gz', '.json', '.txt')):
                continue
            file_path = os.path.join(root, filename)
            try:
                modality, series_dir = process_file(file_path)
            except ValueError:
                continue
            if modality and modality not in result:
                result[modality] = series_dir
                if 'PT' in result and 'CT' in result:
                    return result

    return result
