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
# and meet the required specifications.
#
# Usage:
# The functions in this module can be imported and used in other modules within the pumaz to perform input validation.
#
# ----------------------------------------------------------------------------------------------------------------------

import logging
import os
from pumaz import constants
import nibabel as nib

def select_puma_compliant_subjects(tracer_paths: list, modality_tags: list) -> list:
    """
    Selects the subjects that have files with names that are compliant with the pumaz naming conventions.

    Parameters:
        tracer_paths (list): The list of paths to the tracer directories present in the subject directory.
        modality_tags (list): The list of appropriate modality prefixes that should be attached to the files for them
                              to be pumaz compliant.

    Returns:
        list: The list of tracer paths that are pumaz compliant.
    """
    # Iterate through each subject in the parent directory
    puma_compliant_subjects = []
    for subject_path in tracer_paths:
        # Check if the files have the appropriate modality prefixes
        files = [file for file in os.listdir(subject_path) if file.endswith('.nii') or file.endswith('.nii.gz')]
        prefixes = [file.startswith(tag) for tag in modality_tags for file in files]
        if sum(prefixes) == len(modality_tags):
            puma_compliant_subjects.append(subject_path)

    print(f"{constants.ANSI_ORANGE}Number of puma compliant tracer directories: {len(puma_compliant_subjects)} out of "
          f"{len(tracer_paths)}{constants.ANSI_RESET}")
    logging.info(f"Number of puma compliant tracer directories: {len(puma_compliant_subjects)} out of "
                 f"{len(tracer_paths)}")

    return puma_compliant_subjects
