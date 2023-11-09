#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------------------------------------------------------
# Author: Lalith Kumar Shiyam Sundar | Sebastian Gutschmayer
# Institution: Medical University of Vienna
# Research Group: Quantitative Imaging and Medical Physics (QIMP) Team
# Date: 04.07.2023
# Version: 0.1.0
#
# Description:
# This module shows predefined display messages for the pumaz.
#
# Usage:
# The functions in this module can be imported and used in other modules within the pumaz to show predefined display
# messages.
#
# ----------------------------------------------------------------------------------------------------------------------

import logging
import pyfiglet

from pumaz import constants


def logo():
    """
    Display the PUMA logo.

    :return: None
    :rtype: None
    :Example:
        >>> logo()
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

def citation():
    """
    Display the manuscript citation for PUMA.

    :return: None
    :rtype: None
    :Example:
        >>> citation()
    """
    print(" Sebastian Gutschmayer, Lalith Kumar Shiyam Sundar, PET Universal Multi-tracer Aligner (PUMA) - To be "
          "submitted to Journal of Nuclear Medicine")
    print(" Copyright 2023, Quantitative Imaging and Medical Physics Team, Medical University of Vienna")


def expectations():
    """
    Display the expected modalities for PUMA.

    This function is used to check if the user has provided the correct set of modalities for each tracer set.

    :return: None
    :rtype: None
    :Example:
        >>> expectations()
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


def alignment_strategy():
    """
    Display the alignment strategy for PUMA.

    This function describes the steps involved in aligning PET and CT images in PUMA.

    :return: None
    :rtype: None
    :Example:
        >>> alignment_strategy()
    """
    print(" Step 1: A random PET tracer image will be selected as the reference from the list.")
    print(" Step 2: Each CT image will be resliced to match its corresponding PET tracer image.")
    print(" Step 3: The CT image that pairs with the reference PET tracer image will be set as the reference CT image.")
    print(" Step 4: All other CT images will be aligned to the reference CT image.")
    print(" Step 5: Using the deformation fields derived from the CT images, the corresponding PET tracer images will "
          "be aligned to the reference PET tracer image.")
