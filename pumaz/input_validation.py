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

from pumaz import constants


def select_puma_compliant_subjects(tracer_paths: list, modality_tags: list) -> list:
    """
    Selects the subjects that have the files that have names that are compliant with the pumaz.
    :param tracer_paths: The path to the list of tracer directories that are present in the subject directory.
    :param modality_tags: The list of appropriate modality prefixes that should be attached to the files for them to be moose
    compliant.
    :return: The list of tracer paths that are pumaz compliant.
    """
    # go through each subject in the parent directory
    puma_compliant_subjects = []
    for subject_path in tracer_paths:
        # go through each subject and see if the files have the appropriate modality prefixes
        files = [file for file in os.listdir(subject_path) if file.endswith('.nii') or file.endswith('.nii.gz')]
        prefixes = [file.startswith(tag) for tag in modality_tags for file in files]
        if sum(prefixes) == len(modality_tags):
            puma_compliant_subjects.append(subject_path)
    print(f"{constants.ANSI_ORANGE} Number of puma compliant tracer directories: {len(puma_compliant_subjects)} out of "
          f"{len(tracer_paths)} {constants.ANSI_RESET}")
    logging.info(f" Number of puma compliant tracer directories: {len(puma_compliant_subjects)} out of "
                 f"{len(tracer_paths)}")

    return puma_compliant_subjects



