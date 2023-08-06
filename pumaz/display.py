#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------------------------------------------------------
# Author: Lalith Kumar Shiyam Sundar | Sebastian Gutschmayer
# Institution: Medical University of Vienna
# Research Group: Quantitative Imaging and Medical Physics (QIMP) Team
# Date: 04.07.2023
# Version: 0.1.0
#
# Module: display
#
# Description:
# The `display` module in PUMA-Z is dedicated to presenting user-friendly messages, notifications, and visual cues 
# that enrich the user experience. This module consolidates essential visual feedback mechanisms, ensuring that 
# users receive consistent and intuitive responses as they navigate and interact with the PUMA-Z tool.
# 
# By externalizing and standardizing these display messages, PUMA-Z achieves a cohesive user interface, 
# which is particularly vital when guiding users through complex tasks such as aligning multi-tracer PET/CT images.
#
# Usage:
# Within the PUMA-Z ecosystem, developers and advanced users can readily import and invoke the functions 
# housed in this module. This ensures that various sections of the tool uniformly present messages and feedback, 
# maintaining a harmonized user interaction throughout PUMA-Z operations.
#
# ----------------------------------------------------------------------------------------------------------------------


import pyfiglet
import logging
from pumaz import constants
from . import file_utilities
from pumaz import file_utilities


def logo() -> None:
    """
    Display the PUMA logo along with the ENHANCE community slogan.

    The logo and the slogan are both colored as per the constants defined for them.
    """
    print(' ')
    logo_color_code = constants.ANSI_VIOLET
    slogan_color_code = constants.ANSI_VIOLET
    result = logo_color_code + pyfiglet.figlet_format("PUMA 1.0", font="speed").rstrip() + "\033[0m"
    text = slogan_color_code + "A part of the ENHANCE community. Join us at https://enhance.pet to build the future " \
                               "of " \
                               "PET imaging together." + "\033[0m"
    print(result)
    print(text)
    print(' ')


def citation() -> None:
    """
    Display the manuscript citation for PUMA.
    
    Provides information about the authors, title, and the intended submission journal for the PUMA project.
    """
    print(" Sebastian Gutschmayer, Lalith Kumar Shiyam Sundar, PET Universal Multi-tracer Aligner (PUMA) - To be "
          "submitted to Journal of Nuclear Medicine")
    print(" Copyright 2023, Quantitative Imaging and Medical Physics Team, Medical University of Vienna")


def expectations() -> None:
    """
    Display the expected modalities for PUMA.

    This function informs the user about the modalities PUMA expects, ensuring the correct set is provided for each tracer set.
    Warnings are displayed regarding non-DICOM formats and potential exclusions from analysis.
    """
    # display the expected modalities
    print(f' Expected modalities: {constants.MODALITIES} | Number of required modalities: {len(constants.MODALITIES)} |'
          f' Required prefix for non-DICOM files: {constants.MODALITIES_PREFIX}')
    logging.info(f' Expected modalities: {constants.MODALITIES} | Number of modalities: {len(constants.MODALITIES)} |  '
                 f'Required prefix for non-DICOM files: {constants.MODALITIES_PREFIX}')
    print(
        f"{constants.ANSI_ORANGE} Warning: Any subject datasets in a non-DICOM format that lack the required modalities (" \
        f"as indicated by the file prefix) will not be included in the analysis. {constants.ANSI_RESET}")

    warning_message = " Skipping subjects without the required modalities (check file prefix).\n" \
                      " These subjects will be excluded from analysis and their data will not be used."
    logging.warning(warning_message)

