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


import logging
import os
import time
from datetime import datetime

import colorama
import emoji
import rich_click as click
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

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


def _parse_ignore_regions(ctx, param, value):
    if not value:
        raise click.BadParameter("Provide at least one region (use 'none' to include all regions).")
    choices_list = [label.lower() for label in constants.MOOSE_LABEL_INDEX.values()] + ['none']
    value_list = [item.strip().lower() for item in value.split(',')]
    invalid = [item for item in value_list if item not in choices_list]
    if invalid:
        raise click.BadParameter(
            f"Invalid choice(s): {', '.join(invalid)}. Valid options: {', '.join(choices_list)}."
        )
    return value_list


def _parse_color_map(ctx, param, value):
    if value is None:
        return None

    color_map = {}
    used_colors = set()
    allowed_colors = {'R', 'G', 'B'}

    try:
        for pair in value.split(','):
            key, val = pair.split(':')
            tracer = key.strip()
            color = val.strip().upper()

            if color not in allowed_colors:
                raise click.BadParameter(
                    f"Invalid color '{color}' for tracer '{tracer}'. Allowed values are: R, G, B."
                )

            if color in used_colors:
                raise click.BadParameter(
                    f"Color '{color}' is already assigned. Each color can be used only once."
                )

            color_map[tracer] = color
            used_colors.add(color)
    except ValueError:
        raise click.BadParameter("Colors must be in the format tracer:color,... (e.g. psma:R,fdg:G)")

    return color_map


def run_pipeline(subject_folder, regions_to_ignore, multiplex, custom_colors, color_map,
                 convert_to_dicom, perform_risk_analysis):
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


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "-d",
    "--subject-directory",
    "subject_directory",
    type=click.Path(exists=True, file_okay=False, resolve_path=True, path_type=str),
    required=True,
    help="Directory containing PET/CT tracer folders for a subject.",
)
@click.option(
    "-ir",
    "--ignore-regions",
    callback=_parse_ignore_regions,
    required=True,
    metavar="regions",
    help="Comma-separated regions to ignore during registration (e.g. arms,legs,none).",
)
@click.option(
    "-m",
    "--multiplex",
    is_flag=True,
    default=False,
    help="Generate multiplexed RGB images for aligned PET volumes.",
)
@click.option(
    "-cs",
    "--custom-colors",
    is_flag=True,
    default=False,
    help="Interactively assign colors to tracer images (requires --multiplex).",
)
@click.option(
    "-cm",
    "--color-map",
    callback=_parse_color_map,
    default=None,
    metavar="map",
    help="Set tracer:color pairs (e.g. psma:R,fdg:G). Requires --multiplex.",
)
@click.option(
    "-c2d",
    "--convert-to-dicom",
    is_flag=True,
    default=False,
    help="Convert aligned NIfTI images back to DICOM.",
)
@click.option(
    "-ra",
    "--risk-analysis",
    is_flag=True,
    default=False,
    help="Highlight potential misalignment regions using volume comparisons.",
)
def cli(subject_directory, ignore_regions, multiplex, custom_colors, color_map, convert_to_dicom, risk_analysis):
    """
    Run the PUMA-Z preprocessing and registration pipeline with a richly formatted CLI.
    """
    logging.basicConfig(format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s', level=logging.INFO,
                        filename=datetime.now().strftime('pumaz-v.1.0.0.%H-%M-%d-%m-%Y.log'), filemode='w')
    colorama.init()

    if color_map and not multiplex:
        raise click.UsageError("--color-map requires --multiplex.")
    if custom_colors and not multiplex:
        raise click.UsageError("--custom-colors requires --multiplex.")

    subject_folder = os.path.abspath(subject_directory)
    run_pipeline(subject_folder, ignore_regions, multiplex, custom_colors, color_map, convert_to_dicom, risk_analysis)


def main():
    cli()


if __name__ == "__main__":
    main()
