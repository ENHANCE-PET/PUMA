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
from rich.console import Console

console = Console()

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
    console.print(" TBD", style="white")
    console.print(" Copyright 2023, Quantitative Imaging and Medical Physics Team, Medical University of Vienna",
                  style="white")


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
    console.print(f' Expected anatomical modalities: {constants.ANATOMICAL_MODALITIES} |'
          f' Number of required anatomical modalities: 1 |'
          f' Expected functional modalities: {constants.FUNCTIONAL_MODALITIES} |'
          f' Number of required functional modalities: 1 |'
                  f' Required prefix for non-DICOM files: {constants.MODALITIES_PREFIX}', style='white')
    logging.info(f' Expected anatomical modalities: {constants.ANATOMICAL_MODALITIES} |'
                 f' Number of required anatomical modalities: 1 |'
                 f' Expected functional modalities: {constants.FUNCTIONAL_MODALITIES} |'
                 f' Number of required functional modalities: 1 |'
                 f' Required prefix for non-DICOM files: {constants.MODALITIES_PREFIX}')
    console.print(
        f" Warning: Any subject datasets in a non-DICOM format that lack the required modalities"
        f" (as indicated by the file prefix) will not be included in the analysis.", style="bold magenta")

    warning_message = " Skipping subjects without the required modalities (check file prefix).\n" \
                      " These subjects will be excluded from analysis and their data will not be used."
    logging.warning(warning_message)

