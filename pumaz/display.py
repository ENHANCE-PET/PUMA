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

import pyfiglet
import logging
from pumaz import constants



def logo():
    """
    Display PUMA logo
    :return:
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
    Display manuscript citation
    :return:
    """
    print(" Sebastian Gutschmayer, Lalith Kumar Shiyam Sundar, PET Universal Multi-tracer Aligner (PUMA) - To be "
          "submitted to Journal of Nuclear Medicine")
    print(" Copyright 2023, Quantitative Imaging and Medical Physics Team, Medical University of Vienna")


def expectations():
    """
    Display expected modalities for PUMA. This is used to check if the user has provided the correct set of modalities for each tracer set.
    """
    # display the expected modalities
    print(f' Expected modalities: {constants.MODALITIES} | Number of required modalities: {len(constants.MODALITIES)} |'
          f' Required prefix for non-DICOM files: {constants.MODALITIES_PREFIX}')
    logging.info(f' Expected modalities: {constants.MODALITIES} | Number of modalities: {len(constants.MODALITIES)} |  '
                    f'Required prefix for non-DICOM files: {constants.MODALITIES_PREFIX}')
    print(f"{constants.ANSI_ORANGE} Warning: Any subject datasets in a non-DICOM format that lack the required modalities (" \
    f"as indicated by the file prefix) will not be included in the analysis. {constants.ANSI_RESET}")

    warning_message = " Skipping subjects without the required modalities (check file prefix).\n" \
                      " These subjects will be excluded from analysis and their data will not be used."
    logging.warning(warning_message)