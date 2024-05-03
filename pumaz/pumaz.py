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
import time
from datetime import datetime

import colorama
import emoji
from pumaz import constants
from pumaz import display
from pumaz import download
from pumaz import file_utilities
from pumaz import image_conversion
from pumaz import image_processing
from pumaz import input_validation
from pumaz import resources
from rich.console import Console

console = Console()


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
    logging.basicConfig(format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s', level=logging.INFO,
                        filename=datetime.now().strftime('pumaz-v.1.0.0.%H-%M-%d-%m-%Y.log'), filemode='w')
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

    parser.add_argument("-m", "--multiplex", action='store_true', default=False,
                        help="Multiplex the aligned PT images.", required=False)

    parser.add_argument("-st", "--segment_tumors", action='store_true', default=False,
                        help="Segment tumors in the multiplexed images.", required=False)

    parser.add_argument("-cs", "--custom_colors", action='store_true', default=False,
                        help="Manually assign colors to tracer images.", required=False)

    parser.add_argument("-c2d", "--convert_to_dicom", action='store_true', default=False,
                        help="Convert DICOM images to NIFTI format. Set this to true only if your input is DICOM",
                        required=False)

    args = parser.parse_args()

    subject_folder = os.path.abspath(args.subject_directory)
    regions_to_ignore = args.ignore_regions
    multiplex = args.multiplex
    custom_colors = args.custom_colors
    segment_tumors = args.segment_tumors
    convert_to_dicom = args.convert_to_dicom

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
    # DISPLAYING INPUT CHOICES
    # ----------------------------------
    console.print(f' Multiplexing: {multiplex} | '
                  f'Custom Colors: {custom_colors} | '
                  f'Segment Tumors: {segment_tumors} | ',
                  f'Convert to DICOM: {convert_to_dicom} | ',
                  f'Regions to Ignore: {regions_to_ignore}',
                  style='bold magenta')

    # ----------------------------------
    # DOWNLOADING THE BINARIES
    # ----------------------------------

    print('')
    print(f'{constants.ANSI_VIOLET} {emoji.emojize(":globe_with_meridians:")} BINARIES DOWNLOAD:{constants.ANSI_RESET}')

    print('')
    binary_path = constants.BINARY_PATH
    file_utilities.create_directory(binary_path)
    system_os, system_arch = file_utilities.get_system()
    console.print(f' Detected system: {system_os} | Detected architecture: {system_arch}', style='bold magenta')
    download.download(item_name=f'puma-{system_os}-{system_arch}', item_path=binary_path,
                      item_dict=resources.PUMA_BINARIES)
    file_utilities.set_permissions(constants.GREEDY_PATH, system_os)
    file_utilities.set_permissions(constants.C3D_PATH, system_os)

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
    logging.info(" Standardization complete.")

    # --------------------------------------
    # CHECKING FOR PUMA COMPLIANT SUBJECTS
    # --------------------------------------

    tracer_dirs = [os.path.join(subject_folder, d) for d in os.listdir(subject_folder)
                   if os.path.isdir(os.path.join(subject_folder, d)) and not d.startswith('PUMAZ-v1')]
    puma_compliant_subject_folders = input_validation.select_puma_compliant_subject_folders(tracer_dirs)

    num_subject_folders = len(puma_compliant_subject_folders)
    if num_subject_folders < 1:
        print(
            f'{constants.ANSI_RED} {emoji.emojize(":cross_mark:")} No puma compliant tracer directories found to continue!{constants.ANSI_RESET} {emoji.emojize(":light_bulb:")} See: https://github.com/Keyn34/PUMA#directory-structure-and-naming-conventions-for-puma-%EF%B8%8F')
        return

    # -------------------------------------------------
    # RUNNING PREPROCESSING AND REGISTRATION PIPELINE
    # -------------------------------------------------
    # calculate elapsed time for the entire procedure below
    start_time = time.time()
    print('')
    print(
        f'{constants.ANSI_VIOLET} {emoji.emojize(":rocket:")} RUNNING PREPROCESSING AND REGISTRATION PIPELINE:{constants.ANSI_RESET}')
    print('')
    logging.info(' ')
    logging.info(' RUNNING PREPROCESSING AND REGISTRATION PIPELINE:')
    logging.info(' ')
    puma_dir, ct_dir, pt_dir, mask_dir = image_processing.preprocess(
        puma_compliant_subjects=puma_compliant_subject_folders,
        regions_to_ignore=regions_to_ignore)
    reference_img = image_processing.align(puma_dir, ct_dir, pt_dir, mask_dir)

    # ----------------------------------
    # MULTIPLEXING
    # ----------------------------------

    if multiplex:
        print('')
        print(f'{constants.ANSI_VIOLET} {emoji.emojize(":artist_palette:")} MULTIPLEXING:{constants.ANSI_RESET}')
        print('')
        logging.info(' ')
        logging.info(' MULTIPLEXING:')
        logging.info(' ')
        aligned_pt_dir = os.path.join(puma_dir, constants.ALIGNED_PET_FOLDER)
        rgb_image = os.path.join(aligned_pt_dir, constants.MULTIPLEXED_COMPOSITE_IMAGE)
        image_processing.multiplex(aligned_pt_dir, '*nii*', 'PET',
                                   rgb_image, custom_colors)
        grayscale_image = os.path.join(aligned_pt_dir, constants.GRAYSCALE_COMPOSITE_IMAGE)
        image_processing.rgb2gray(rgb_image, grayscale_image)
        if segment_tumors:
            print('')
            print(
                f'{constants.ANSI_VIOLET} {emoji.emojize(":face_with_medical_mask:")} SEGMENTING TUMORS:{constants.ANSI_RESET}')
            print('')
            print(f' {constants.ANSI_ORANGE}Segmentation may take a few minutes...{constants.ANSI_RESET}')
            seg_dir = os.path.join(puma_dir, constants.SEGMENTATION_FOLDER)
            file_utilities.create_directory(seg_dir)
            file_utilities.copy_reference_image(grayscale_image, seg_dir, constants.LIONZ_PREFIX)
            output_dir = os.path.join(seg_dir, constants.LIONZ_OUTPUT_DIR)
            file_utilities.create_directory(output_dir)
            image_processing.segment_tumors(seg_dir, output_dir)
            console.print(f' Segmentation complete.', style='bold green')

    if convert_to_dicom:
        print('')
        print(f'{constants.ANSI_VIOLET} {emoji.emojize(":file_folder:")} CONVERTING TO DICOM:{constants.ANSI_RESET}')
        print('')
        logging.info(' ')
        logging.info(' CONVERTING TO DICOM:')
        logging.info(' ')
        n2dConverter = image_conversion.NiftiToDicomConverter(
            subject_folder=subject_folder,
            puma_dir=puma_dir,
        )
        n2dConverter.set_reference_image(reference_img)
        n2dConverter.convert_to_dicom(puma_compliant_subject_folders=puma_compliant_subject_folders)

    end_time = time.time()
    elapsed_time = end_time - start_time
    # show elapsed time in minutes and round it to 2 decimal places
    elapsed_time = round(elapsed_time / 60, 2)
    console.print(f" 🐾 PUMA has successfully completed the hunt in {elapsed_time} minutes."
                  f" Track down your results in the directory: {puma_dir} 🐾", style='white')
