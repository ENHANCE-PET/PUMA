#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------------------------------------------------------
# Author: Lalith Kumar Shiyam Sundar | Sebastian Gutschmayer
# Institution: Medical University of Vienna
# Research Group: Quantitative Imaging and Medical Physics (QIMP) Team
# Date: 07.07.2023
# Version: 1.0.0
#
# Module: input_validation
#
# Description:
# The `input_validation` module stands guard at the gates of PUMA-Z, ensuring that only valid, compliant data enters its realm. 
# As the name suggests, it is tasked with a critical function—ensuring that every piece of input data adheres to PUMA-Z's stringent 
# requirements. In the intricate maze of medical imaging data, consistency, accuracy, and standardization are paramount.
#
# Leveraging meticulous algorithms and smart logic, this module sifts through the input data, differentiating between compliant and 
# non-compliant data. Whether it's checking naming conventions or ensuring that data modalities match expected standards, the 
# `input_validation` module doesn't miss a beat.
#
# Usage:
# The primary purpose of this module is to serve as a sentinel, invoked by other PUMA-Z modules whenever data is ingested. By 
# incorporating this module's functions, developers can be assured that PUMA-Z's internal operations always work on pristine, 
# compliant data, setting the stage for high-quality outputs.
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
