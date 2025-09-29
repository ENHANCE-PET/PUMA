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

    def parse_color_dict(value):
        try:
            color_map = {}
            used_colors = set()
            allowed_colors = {'R', 'G', 'B'}

            for pair in value.split(','):
                key, val = pair.split(':')
                key = key.strip()
                val = val.strip().upper()

                if val not in allowed_colors:
                    raise argparse.ArgumentTypeError(f"Invalid color '{val}' for tracer '{key}'. Allowed values are: R, G, B.")

                if val in used_colors:
                    raise argparse.ArgumentTypeError(f"Color '{val}' is already assigned. Each color can be used only once.")

                color_map[key] = val
                used_colors.add(val)

            return color_map

        except ValueError:
            raise argparse.ArgumentTypeError("Colors must be in the format tracer:color,...")

    parser.add_argument("-ir", "--ignore_regions", type=str2list,
                        help="Comma-separated list of regions to ignore during registration e.g. arms,legs,"
                             "none. 'none' indicates no regions to ignore.", required=True)

    parser.add_argument("-m", "--multiplex", action='store_true', default=False,
                        help="Multiplex the aligned PT images.", required=False)

    parser.add_argument("-cs", "--custom_colors", action='store_true', default=False,
                        help="Manually assign colors to tracer images.", required=False)

    parser.add_argument("-cm", "--color_map", type=parse_color_dict, default=None,
                        help="Specify custom colors as tracer (e.g. psma:R,fdg:G) (requires -m)")

    parser.add_argument("-c2d", "--convert_to_dicom", action='store_true', default=False,
                        help="Convert DICOM images to NIFTI format. Set this to true only if your input is DICOM",
                        required=False)

    parser.add_argument("-ra", "--risk_analysis", action='store_true', default=False,
                        help="Highlight areas of misalignment in the images.",
                        required=False)

    args = parser.parse_args()

    subject_folder = os.path.abspath(args.subject_directory)
    regions_to_ignore = args.ignore_regions
    multiplex = args.multiplex
    custom_colors = args.custom_colors
    color_map = args.color_map
    convert_to_dicom = args.convert_to_dicom
    perform_risk_analysis = args.risk_analysis

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
                  f'Color map: {color_map} |',
                  f'Convert to DICOM: {convert_to_dicom} | ',
                  f'Regions to Ignore: {regions_to_ignore} | ',
                  f'Risk Analysis: {perform_risk_analysis}',
                  style='bold yellow')

    # ----------------------------------
    # DOWNLOADING THE BINARIES
    # ----------------------------------

    print('')
    print(f'{constants.ANSI_VIOLET} {emoji.emojize(":globe_with_meridians:")} BINARIES DOWNLOAD:{constants.ANSI_RESET}')

    print('')
    binary_path = constants.BINARY_PATH
    file_utilities.create_directory(binary_path)
    system_os, system_arch = file_utilities.get_system()
    console.print(f' Detected system: {system_os} | Detected architecture: {system_arch}', style='bold yellow')
    download.download(item_name=f'puma-{system_os}-{system_arch}', item_path=binary_path, item_dict=resources.PUMA_BINARIES)
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
        print(f'{constants.ANSI_RED} {emoji.emojize(":cross_mark:")} No puma compliant tracer directories found to continue!{constants.ANSI_RESET} {emoji.emojize(":light_bulb:")} See: https://github.com/Keyn34/PUMA#directory-structure-and-naming-conventions-for-puma-%EF%B8%8F')
        return

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
    puma_dir, ct_dir, pt_dir, mask_dir = image_processing.preprocess(puma_compliant_subjects=puma_compliant_subject_folders,
                                                                     regions_to_ignore=regions_to_ignore)
    reference_mask, reference_ct, reference_pt = image_processing.align(puma_dir, ct_dir, pt_dir, mask_dir)

    # store the reference images as a dictionary
    reference_dict = {
        'reference_mask': reference_mask,
        'reference_ct': reference_ct,
        'reference_pt': reference_pt
    }

    if perform_risk_analysis:
        # ---------------------------------------
        # DISPLAY POSSIBLE AREAS OF MISALIGNMENT
        # ---------------------------------------
        print('')
        print(f'{constants.ANSI_VIOLET} {emoji.emojize(":face_screaming_in_fear:")} POSSIBLE AREAS OF MISALIGNMENT:{constants.ANSI_RESET}')
        print('')
        logging.info(' ')
        logging.info(' DISPLAYING POSSIBLE AREAS OF MISALIGNMENT:')
        logging.info(' ')
        misaligned_regions = image_processing.display_misalignment(puma_dir, reference_dict)
        reference_filename = os.path.basename(reference_dict["reference_mask"])
        image_processing.display_misalignment_table(misaligned_regions, reference_filename)


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
        image_processing.multiplex(aligned_pt_dir, '*nii*', 'PET', rgb_image, custom_colors, color_map)
        grayscale_image = os.path.join(aligned_pt_dir, constants.GRAYSCALE_COMPOSITE_IMAGE)
        image_processing.rgb2gray(rgb_image, grayscale_image)

    if convert_to_dicom:
        print('')
        print(f'{constants.ANSI_VIOLET} {emoji.emojize(":file_folder:")} CONVERTING TO DICOM:{constants.ANSI_RESET}')
        print('')
        logging.info(' ')
        logging.info(' CONVERTING TO DICOM:')
        logging.info(' ')
        n2dConverter = image_conversion.NiftiToDicomConverter(subject_folder=subject_folder, puma_dir=puma_dir)
        n2dConverter.set_reference_image(reference_mask)
        n2dConverter.convert_to_dicom(puma_compliant_subject_folders=puma_compliant_subject_folders)

    end_time = time.time()
    elapsed_time = end_time - start_time
    # show elapsed time in minutes and round it to 2 decimal places
    elapsed_time = round(elapsed_time / 60, 2)
    console.print(f" 🐾 PUMA has successfully completed the hunt in {elapsed_time} minutes."
                  f" Track down your results in the directory: {puma_dir} 🐾", style='white')