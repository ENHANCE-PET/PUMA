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
import colorama
import emoji
import logging
import os
import time
from datetime import datetime

from pumaz import constants
from pumaz import display
from pumaz import download
from pumaz import file_utilities
from pumaz import image_conversion
from pumaz import image_processing
from pumaz import input_validation
from pumaz import resources

logging.basicConfig(format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s', level=logging.INFO,
                    filename=datetime.now().strftime('pumaz-v.1.0.0.%H-%M-%d-%m-%Y.log'),
                    filemode='w')


def main():
    """
    Run the PUMA-Z preprocessing and registration pipeline.

    This function standardizes input data to NIFTI format, checks for PUMA-compliant subjects, and runs the preprocessing
    and registration pipeline. It also downloads the necessary binaries and sets the appropriate permissions.

    :return: None
    :rtype: None
    :Example:
        >>> main()
    """
    colorama.init()

    parser = argparse.ArgumentParser()

    parser.add_argument("-d", "--subject_directory", type=str,
                        help="Subject directory containing the different PET/CT images of the same subject",
                        required=True)

    def str2list(value):
        choices_list = list(constants.MOOSE_LABEL_INDEX.values()) + ['none']
        value_list = value.lower().split(',')
        if all(item in choices_list for item in value_list):
            return value_list
        else:
            raise argparse.ArgumentTypeError(f"invalid choice: {value_list} (choose from {choices_list})")

    parser.add_argument("-ir", "--ignore_regions", type=str2list,
                        help="Comma-separated list of regions to ignore during registration e.g. arms,legs,"
                             "none. 'none' indicates no regions to ignore.", required=True)

    args = parser.parse_args()

    subject_folder = os.path.abspath(args.subject_directory)
    regions_to_ignore = args.ignore_regions

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
    print(f'{constants.ANSI_VIOLET} {emoji.emojize(":memo:")} NOTE:{constants.ANSI_RESET}')
    print(' ')
    display.expectations()

    # ----------------------------------
    # DOWNLOADING THE BINARIES
    # ----------------------------------

    print('')
    print(f'{constants.ANSI_VIOLET} {emoji.emojize(":globe_with_meridians:")} BINARIES DOWNLOAD:{constants.ANSI_RESET}')

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
    print(f'{constants.ANSI_VIOLET} {emoji.emojize(":magnifying_glass_tilted_left:")} STANDARDIZING INPUT DATA TO '
          f'NIFTI:{constants.ANSI_RESET}')
    print('')
    logging.info(' ')
    logging.info(' STANDARDIZING INPUT DATA TO NIFTI:')
    logging.info(' ')
    image_conversion.standardize_to_nifti(subject_folder)
    print(f"{constants.ANSI_GREEN} Standardization complete.{constants.ANSI_RESET}")
    logging.info(" Standardization complete.")

    # --------------------------------------
    # CHECKING FOR PUMA COMPLIANT SUBJECTS
    # --------------------------------------

    tracer_dirs = [os.path.join(subject_folder, d) for d in os.listdir(subject_folder) if
                   os.path.isdir(os.path.join(subject_folder, d))]
    puma_compliant_subjects = input_validation.select_puma_compliant_subjects(tracer_dirs, constants.MODALITIES)

    # -------------------------------------------------
    # RUNNING PREPROCESSING AND REGISTRATION PIPELINE
    # -------------------------------------------------
    # calculate elapsed time for the entire procedure below
    start_time = time.time()
    print('')
    print(f'{constants.ANSI_VIOLET} {emoji.emojize(":rocket:")} RUNNING PREPROCESSING AND REGISTRATION PIPELINE:{constants.ANSI_RESET}')
    print('')
    logging.info(' ')
    logging.info(' RUNNING PREPROCESSING AND REGISTRATION PIPELINE:')
    logging.info(' ')
    puma_dir, ct_dir, pt_dir, mask_dir = image_processing.preprocess(puma_compliant_subjects=puma_compliant_subjects,
                                                                     regions_to_ignore=regions_to_ignore)
    image_processing.align(puma_dir, ct_dir, pt_dir, mask_dir)
    end_time = time.time()
    elapsed_time = end_time - start_time
    # show elapsed time in minutes and round it to 2 decimal places
    elapsed_time = round(elapsed_time / 60, 2)
    print(
        f"{constants.ANSI_GREEN} 🐾 PUMA has successfully completed the hunt in {elapsed_time} minutes."
        f" Track down your results in the directory: {puma_dir} 🐾{constants.ANSI_RESET}"
    )



