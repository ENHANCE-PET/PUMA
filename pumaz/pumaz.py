#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------------------------------------------------------
# Authors: Lalith Kumar Shiyam Sundar | Sebastian Gutschmayer
# Institution: Medical University of Vienna
# Research Group: Quantitative Imaging and Medical Physics (QIMP) Team
# Date: 04.07.2023
# Version: 0.1.0
# 
#
# Module: PUMAz (PET Universal Multi-tracer Aligner - Z Edition)
#
# Description:
# PUMAz (pronounced as PUMA-Zee) is an advanced imaging tool designed to seamlessly align multi-tracer PET/CT 
# images of the same patient, regardless of when they were acquired or the different tracers used. Born out 
# of QIMP's tradition of innovative imaging tools, the 'Z' in PUMAz symbolizes the continuation of a legacy 
# combined with a future-forward vision.
#
# This module is the beating heart of PUMAz. It drives the main execution sequence, encompassing everything 
# from initializing the environment, handling user input, to running the complete image preprocessing and 
# registration pipeline. Alongside standardizing image data, this module ensures that the processed images 
# are PUMA-compliant and then aligns them for consistency.
#
# Usage:
# This module is designed to be run as the primary script to execute the PUMAz functionalities. Users can 
# pass their subject directory as a command-line argument to start the process.
# While the variables in this module are meant for internal use, advanced users or developers can access 
# them for further extensions or modifications within the PUMAz framework.
# ----------------------------------------------------------------------------------------------------------------------



import argparse
import logging
import os
import sys
import time
from datetime import datetime
import colorama
import emoji

from pumaz import display
from pumaz import constants
from pumaz import file_utilities
from pumaz import download
from pumaz import resources
from pumaz import image_conversion
from pumaz import input_validation
from pumaz import image_processing

logging.basicConfig(format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s', level=logging.INFO,
                    filename=datetime.now().strftime('pumaz-v.1.0.0.%H-%M-%d-%m-%Y.log'),
                    filemode='w')


def main():
    """
    Main execution function for the PUMA-Z program.
    
    This function:
    1. Initializes the colorama and argument parser for command-line inputs.
    2. Validates and prepares the user-provided subject directory.
    3. Downloads necessary binaries for the platform.
    4. Standardizes input image data to NIFTI format.
    5. Checks for PUMA-compliant tracer directories.
    6. Runs the preprocessing and registration pipeline.
    """
    
    # Initialize colorama and command-line arguments parser
    colorama.init()

    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--subject_directory", type=str,
                        help="Subject directory containing the different PET/CT images of the same subject",
                        required=True)
    args = parser.parse_args()

    # Resolve the subject directory path
    subject_folder = os.path.abspath(args.subject_directory)

    # Display the PUMA logo and citation information
    display.logo()
    display.citation()

    # Log the starting of PUMA-Z program
    logging.info('----------------------------------------------------------------------------------------------------')
    logging.info('                                     STARTING PUMA-Z V.1.0.0                                       ')
    logging.info('----------------------------------------------------------------------------------------------------')

    # Input validation and preparation
    logging.info(' ')
    logging.info('- Subject directory: ' + subject_folder)
    logging.info(' ')
    print(' ')
    print(f'{constants.ANSI_VIOLET} {emoji.emojize(":memo:")} NOTE:{constants.ANSI_RESET}')
    print(' ')
    display.expectations()

    # Download necessary binaries for the platform
    print('')
    print(f'{constants.ANSI_VIOLET} {emoji.emojize(":globe_with_meridians:")} BINARIES DOWNLOAD:{constants.ANSI_RESET}')
    binary_path = constants.BINARY_PATH
    file_utilities.create_directory(binary_path)
    system_os, system_arch = file_utilities.get_system()
    print(f'{constants.ANSI_ORANGE} Detected system: {system_os} | Detected architecture: {system_arch}'
          f'{constants.ANSI_RESET}')
    download.download(item_name=f'greedy-{system_os}-{system_arch}', item_path=binary_path,
                      item_dict=resources.GREEDY_BINARIES)
    file_utilities.set_permissions(constants.GREEDY_PATH, system_os)

    # Standardize input image data to NIFTI format
    print('')
    print(f'{constants.ANSI_VIOLET} {emoji.emojize(":magnifying_glass_tilted_left:")} STANDARDIZING INPUT DATA TO '
          f'NIFTI:{constants.ANSI_RESET}')
    logging.info(' STANDARDIZING INPUT DATA TO NIFTI:')
    image_conversion.standardize_to_nifti(subject_folder)
    print(f"{constants.ANSI_GREEN} Standardization complete.{constants.ANSI_RESET}")
    logging.info(" Standardization complete.")

    # Check and filter PUMA-compliant tracer directories
    tracer_dirs = [os.path.join(subject_folder, d) for d in os.listdir(subject_folder) if
                   os.path.isdir(os.path.join(subject_folder, d))]
    puma_compliant_subjects = input_validation.select_puma_compliant_subjects(tracer_dirs, constants.MODALITIES)

    # Run preprocessing and registration pipeline
    start_time = time.time()
    print('')
    print(f'{constants.ANSI_VIOLET} {emoji.emojize(":rocket:")} RUNNING PREPROCESSING AND REGISTRATION PIPELINE:{constants.ANSI_RESET}')
    logging.info(' RUNNING PREPROCESSING AND REGISTRATION PIPELINE:')
    puma_dir, ct_dir, pt_dir, mask_dir = image_processing.preprocess(puma_compliant_subjects)
    image_processing.align(puma_dir, ct_dir, pt_dir, mask_dir)
    end_time = time.time()
    elapsed_time = end_time - start_time
    elapsed_time = round(elapsed_time / 60, 2)
    print(f'{constants.ANSI_GREEN} {emoji.emojize(":hourglass_done:")} Preprocessing and registration complete.'
          f' Elapsed time: {elapsed_time} minutes! {emoji.emojize(":partying_face:")} Aligned images are stored in'
          f' {puma_dir}! Look for the directories with prefix "aligned"! {constants.ANSI_RESET}')


