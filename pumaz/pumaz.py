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
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

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
    console.print()
    display.logo()
    console.print()
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
    options_summary = [
        f"Multiplexing: {multiplex}",
        f"Custom Colors: {custom_colors}",
        f"Color map: {color_map}",
        f"Convert to DICOM: {convert_to_dicom}",
        f"Regions to Ignore: {', '.join(regions_to_ignore) if regions_to_ignore else 'None'}",
        f"Risk Analysis: {perform_risk_analysis}",
    ]

    console.print()
    display.expectations(options_summary)

    # ----------------------------------
    # DISPLAYING INPUT CHOICES
    # ----------------------------------
    # Options already displayed inside expectations panel

    # ----------------------------------
    # DOWNLOADING THE BINARIES
    # ----------------------------------

    display.section("Binaries Download", ":globe_with_meridians:")
    binary_path = constants.BINARY_PATH
    file_utilities.create_directory(binary_path)
    system_os, system_arch = file_utilities.get_system()
    console.print(
        f" [{constants.PUMAZ_COLORS['text']}]Detected system: {system_os} | Detected architecture: {system_arch}[/]"
    )
    download.download(item_name=f'puma-{system_os}-{system_arch}', item_path=binary_path, item_dict=resources.PUMA_BINARIES)
    file_utilities.set_permissions(constants.GREEDY_PATH, system_os)
    file_utilities.set_permissions(constants.C3D_PATH, system_os)
    console.print()

    # ----------------------------------
    # INPUT STANDARDIZATION
    # ----------------------------------

    display.section("Standardizing Input Data to NIFTI", ":magnifying_glass_tilted_left:")
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
    console.print()

    num_subject_folders = len(puma_compliant_subject_folders)
    if num_subject_folders < 1:
        error_panel = Panel(
            Text(
                "No PUMA-compliant tracer directories found to continue!\n"
                "See: https://github.com/Keyn34/PUMA#directory-structure-and-naming-conventions-for-puma-%EF%B8%8F",
                style="white",
            ),
            title=f"{emoji.emojize(':cross_mark:')} Error",
            border_style=constants.PUMAZ_COLORS["error"],
            padding=(1, 2),
        )
        console.print(error_panel)
        return

    # -------------------------------------------------
    # RUNNING PREPROCESSING AND REGISTRATION PIPELINE
    # -------------------------------------------------
    # calculate elapsed time for the entire procedure below
    start_time = time.time()
    display.section("Running Preprocessing and Registration Pipeline", ":rocket:")
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
    console.print()
    timeline_steps = [
        ("MOOSE AI CT segmentation: clin_ct_body", True),
        ("MOOSE AI CT segmentation: clin_ct_PUMA", True),
        ("Alignment: Greedy registration", True),
    ]
    timeline_line = Text(" ")
    for idx, (label, done) in enumerate(timeline_steps):
        icon = "🟢" if done else "⚪"
        color = constants.PUMAZ_COLORS["success"] if done else constants.PUMAZ_COLORS["warning"]
        timeline_line.append(icon, style=color)
        timeline_line.append(f" {label} ", style=constants.PUMAZ_COLORS["muted"])
        if idx < len(timeline_steps) - 1:
            timeline_line.append("→", style=constants.PUMAZ_COLORS["muted"])
            timeline_line.append(" ", style=constants.PUMAZ_COLORS["muted"])
    console.print(timeline_line)

    if perform_risk_analysis:
        # ---------------------------------------
        # DISPLAY POSSIBLE AREAS OF MISALIGNMENT
        # ---------------------------------------
        display.section("Possible Areas of Misalignment", ":face_screaming_in_fear:")
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
        console.print()
        display.section("Multiplexing", ":artist_palette:")
        logging.info(' ')
        logging.info(' MULTIPLEXING:')
        logging.info(' ')
        aligned_pt_dir = os.path.join(puma_dir, constants.ALIGNED_PET_FOLDER)
        rgb_image = os.path.join(aligned_pt_dir, constants.MULTIPLEXED_COMPOSITE_IMAGE)
        image_processing.multiplex(aligned_pt_dir, '*nii*', 'PET', rgb_image, custom_colors, color_map)
        grayscale_image = os.path.join(aligned_pt_dir, constants.GRAYSCALE_COMPOSITE_IMAGE)
        image_processing.rgb2gray(rgb_image, grayscale_image)

    if convert_to_dicom:
        display.section("Converting to DICOM", ":file_folder:")
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
    success_panel = Panel(
        Text(
            f"PUMA completed in {elapsed_time} minutes. Results available in: {puma_dir}",
            style="white",
            justify="center",
        ),
        border_style=constants.PUMAZ_COLORS["border"],
        padding=(1, 2),
    )
    console.print(success_panel)


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
    PUMA (PET Universal Multi-tracer Aligner) standardizes, registers, and multiplexes serial PET/CT studies.
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
