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
# The main module of the pumaz. It contains the main function that is executed when the pumaz is run.
#
# Usage:
# The variables in this module can be imported and used in other modules within the pumaz.
#
# ----------------------------------------------------------------------------------------------------------------------


import argparse
import logging
import os
import sys
import time
from datetime import datetime
import colorama

from pumaz import display
from pumaz import constants
from pumaz import file_utilities
from pumaz import download
from pumaz import resources
from pumaz import image_conversion

logging.basicConfig(format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s', level=logging.INFO,
                    filename=datetime.now().strftime('pumaz-v.1.0.0.%H-%M-%d-%m-%Y.log'),
                    filemode='w')


def main():
    colorama.init()

    parser = argparse.ArgumentParser()

    parser.add_argument("-d", "--subject_directory", type=str,
                        help="Subject directory containing the different PET/CT images of the same subject",
                        required=True)

    args = parser.parse_args()

    subject_folder = os.path.abspath(args.subject_directory)

    display.logo()
    display.citation()

    logging.info('----------------------------------------------------------------------------------------------------')
    logging.info('                                     STARTING PUMA-Z V.1.0.0                                       ')
    logging.info('----------------------------------------------------------------------------------------------------')

    # ----------------------------------
    # INPUT VALIDATION AND PREPARATION
    # ----------------------------------

    logging.info(' ')
    logging.info('- Subject directory: ' + subject_folder)
    logging.info(' ')
    print(' ')
    print(f'{constants.ANSI_VIOLET} NOTE:{constants.ANSI_RESET}')
    print(' ')
    display.expectations()

    # ----------------------------------
    # DOWNLOADING THE BINARIES
    # ----------------------------------

    print('')
    print(f'{constants.ANSI_VIOLET} BINARIES DOWNLOAD:{constants.ANSI_RESET}')
    print('')
    binary_path = constants.BINARY_PATH
    file_utilities.create_directory(binary_path)
    system_os, system_arch = file_utilities.get_system()
    print(f'{constants.ANSI_ORANGE} Detected system: {system_os} | Detected architecture: {system_arch}'
          f'{constants.ANSI_RESET}')
    download.download(item_name=f'greedy-{system_os}-{system_arch}', item_path=binary_path,
                      item_dict=resources.GREEDY_BINARIES)
    file_utilities.set_permissions(constants.GREEDY_PATH, system_os)

    # ----------------------------------
    # INPUT STANDARDIZATION
    # ----------------------------------

    print('')
    print(f'{constants.ANSI_VIOLET} STANDARDIZING INPUT DATA TO NIFTI:{constants.ANSI_RESET}')
    print('')
    logging.info(' ')
    logging.info(' STANDARDIZING INPUT DATA TO NIFTI:')
    logging.info(' ')
    image_conversion.standardize_to_nifti(subject_folder)
    print(f"{constants.ANSI_GREEN} Standardization complete.{constants.ANSI_RESET}")
    logging.info(" Standardization complete.")
