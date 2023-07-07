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

import constants


def logo():
    """
    Display PUMA logo
    :return:
    """
    print(' ')
    logo_color_code = constants.ANSI_VIOLET
    slogan_color_code = constants.ANSI_VIOLET
    result = logo_color_code + pyfiglet.figlet_format(" PUMA", font="speed").rstrip() + "\033[0m"
    text = slogan_color_code + " A part of the ENHANCE community. Join us at www.enhance.pet to build the future of " \
                               "PET imaging together." + "\033[0m"
    print(result)
    print(text)
    print(' ')


def citation():
    """
    Display manuscript citation
    :return:
    """
    print(" Sebastian Gutschmayer, Lalith Kumar Shiyam Sundar, PET Universal Multi-tracer Aligner (PUMA) - To be submitted to Journal of Nuclear Medicine")
    print(" Copyright 2023, Quantitative Imaging and Medical Physics Team, Medical University of Vienna")



def expectations() -> list:
    """
    Display expected modalities for PUMA. This is used to check if the user has provided the correct set of modalities for each tracer set.
    :return: list of modalities
    """
    # display the expected modalities
    print(f' Expected modalities: {constants.MODALITIES} | Number of modalities: {len(constants.MODALITIES)} |  Required prefix for non-DICOM files: {constants.MODALITIES_PREFIX}')
