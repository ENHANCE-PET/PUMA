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
from pathlib import Path

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


def _print_panel(title: str, lines: list[str], border_color: str) -> None:
    message = Text(justify="left")
    for line in lines:
        message.append(f"{line}\n")
    console.print(
        Panel(
            Align.left(message),
            title=Text(title, style=f"bold {border_color}"),
            border_style=border_color,
            padding=(1, 2),
        )
    )


def _binary_override_help() -> list[str]:
    return [
        "Set PUMAZ_BINARY_PATH to point to a prepared binaries folder:",
        "  • PowerShell     : setx PUMAZ_BINARY_PATH \"C:\\\\path\\\\to\\\\pumaz\\\\bin\"",
        "  • Command Prompt : set PUMAZ_BINARY_PATH=C:\\\\path\\\\to\\\\pumaz\\\\bin",
        "  • Bash/Zsh       : export PUMAZ_BINARY_PATH=\"/path/to/pumaz/bin\"",
        "Restart your shell after updating the environment variable.",
    ]


def perform_environment_check() -> bool:
    """Check whether registration binaries are present and executable."""
    binary_path = constants.BINARY_PATH
    info_lines = [f"Binary directory: {binary_path}"]
    issues: list[str] = []

    if not os.path.isdir(binary_path):
        issues.append("Binary directory does not exist.")
    if not os.access(binary_path, os.W_OK):
        issues.append("Current user lacks write access to the binary directory.")

    for name, path in (("greedy", constants.GREEDY_PATH), ("c3d", constants.C3D_PATH)):
        if os.path.isfile(path):
            if os.access(path, os.X_OK):
                info_lines.append(f"{name}: {path} (executable)")
            else:
                issues.append(f"{name} exists but is not executable: {path}")
        else:
            issues.append(f"{name} missing at expected path: {path}")

    if issues:
        _print_panel(
            f"{emoji.emojize(':toolbox:')} Environment Verification",
            info_lines + ["", "Issues detected:"] + [f"• {issue}" for issue in issues] + [""] + _binary_override_help(),
            constants.PUMAZ_COLORS["warning"],
        )
        return False

    _print_panel(
        f"{emoji.emojize(':check_mark_button:')} Environment Verification",
        info_lines + ["", "All required binaries are present and executable."],
        constants.PUMAZ_COLORS["success"],
    )
    return True


def _parse_ignore_regions(ctx, param, value):
    if not value:
        if ctx.params.get("verify_environment"):
            return []
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

    version_message = f"STARTING PUMA-Z V{constants.PUMAZ_VERSION}"
    logging.info('-' * 100)
    logging.info(version_message.center(100))
    logging.info('-' * 100)

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
    display.expectations(options_summary, subject_folder)

    # ----------------------------------
    # DISPLAYING INPUT CHOICES
    # ----------------------------------
    # Options already displayed inside expectations panel

    # ----------------------------------
    # DOWNLOADING THE BINARIES
    # ----------------------------------

    display.section("Binaries Download", ":globe_with_meridians:")
    binary_path = constants.BINARY_PATH
    try:
        file_utilities.create_directory(binary_path)
    except OSError as exc:
        _print_panel(
            f"{emoji.emojize(':warning:')} Binary Directory Error",
            [
                f"Unable to create or access the binaries directory at {binary_path}.",
                f"System error: {exc}",
            ] + _binary_override_help(),
            constants.PUMAZ_COLORS["error"],
        )
        raise SystemExit(1)
    if not os.access(binary_path, os.W_OK):
        _print_panel(
            f"{emoji.emojize(':locked:')} Insufficient Permissions",
            [
                f"The current user cannot write to {binary_path}.",
            ] + _binary_override_help(),
            constants.PUMAZ_COLORS["error"],
        )
        raise SystemExit(1)
    system_os, system_arch = file_utilities.get_system()
    console.print(
        f" [{constants.PUMAZ_COLORS['text']}]Detected system: {system_os} | Detected architecture: {system_arch}[/]"
    )
    try:
        download.download(
            item_name=f'puma-{system_os}-{system_arch}',
            item_path=binary_path,
            item_dict=resources.PUMA_BINARIES,
            expected_files=[constants.GREEDY_PATH, constants.C3D_PATH],
        )
    except download.BinaryDownloadError as exc:
        _print_panel(
            f"{emoji.emojize(':no_entry:')} Download Failed",
            [
                str(exc),
                "If this system has restricted network access, download the binaries manually and place them in the binaries directory.",
            ] + _binary_override_help(),
            constants.PUMAZ_COLORS["error"],
        )
        raise SystemExit(1)
    except download.BinaryExtractionError as exc:
        _print_panel(
            f"{emoji.emojize(':warning:')} Extraction Failed",
            [
                str(exc),
                "Delete the partial archive and retry, or provide a verified copy manually.",
            ],
            constants.PUMAZ_COLORS["error"],
        )
        raise SystemExit(1)
    try:
        file_utilities.set_permissions(constants.GREEDY_PATH, system_os)
        file_utilities.set_permissions(constants.C3D_PATH, system_os)
    except file_utilities.PermissionSetupError as exc:
        details = [f"Binary path: {exc.file_path}", str(exc)]
        if exc.hint and "PUMAZ_BINARY_PATH" in exc.hint:
            details.append("")
            details.extend(_binary_override_help())
        _print_panel(
            f"{emoji.emojize(':locked_with_pen:')} Permission Setup Failed",
            details,
            constants.PUMAZ_COLORS["error"],
        )
        raise SystemExit(1)
    for name, path in (("greedy", constants.GREEDY_PATH), ("c3d", constants.C3D_PATH)):
        if not os.path.isfile(path) or not os.access(path, os.X_OK):
            _print_panel(
                f"{emoji.emojize(':warning:')} Binary Validation Failed",
                [
                    f"{name} was not located at {path} or is not executable.",
                ] + _binary_override_help(),
                constants.PUMAZ_COLORS["error"],
            )
            raise SystemExit(1)
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
    try:
        puma_compliant_subject_folders = input_validation.select_puma_compliant_subject_folders(tracer_dirs)
    except input_validation.MissingModalitiesError as exc:
        error_lines = Text(justify="left", style=constants.PUMAZ_COLORS["error"])
        error_lines.append(
            f"{emoji.emojize(':cross_mark:')} Missing required modalities detected:\n",
            style=f"bold {constants.PUMAZ_COLORS['error']}",
        )
        for subject_path, reasons in exc.failures:
            error_lines.append(f" • {subject_path}\n")
            for reason in reasons:
                error_lines.append(f"    - {reason}\n")
        console.print(
            Panel(
                Align.left(error_lines),
                border_style=constants.PUMAZ_COLORS["error"],
                padding=(1, 2),
            )
        )
        raise
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


def run_batch(subject_directories, ignore_regions, multiplex, custom_colors, color_map, convert_to_dicom,
              perform_risk_analysis):
    """
    Run the PUMAZ pipeline for multiple subject directories, continuing past failures.
    """
    total_subjects = len(subject_directories)
    failures = []
    for index, subject_folder in enumerate(subject_directories, start=1):
        console.print()
        console.rule(f"[{constants.PUMAZ_COLORS['secondary']}]Subject {index}/{total_subjects}: {subject_folder}")
        try:
            run_pipeline(
                subject_folder,
                ignore_regions,
                multiplex,
                custom_colors,
                color_map,
                convert_to_dicom,
                perform_risk_analysis,
            )
        except KeyboardInterrupt:
            console.print()
            console.print(
                Panel(
                    Text("Batch execution interrupted by user.", style=constants.PUMAZ_COLORS["warning"]),
                    border_style=constants.PUMAZ_COLORS["warning"],
                    padding=(1, 2),
                )
            )
            raise
        except SystemExit as exc:
            logging.exception("PUMAZ exited for subject %s", subject_folder)
            code = exc.code
            if code is None or code == 0:
                error_message = "SystemExit"
            elif isinstance(code, int):
                error_message = f"SystemExit({code})"
            else:
                error_message = str(code)
            failures.append((subject_folder, error_message))
            console.print(
                Panel(
                    Text(
                        f"{emoji.emojize(':cross_mark:')} Failed subject: {subject_folder}\nReason: {error_message}",
                        style=constants.PUMAZ_COLORS["error"],
                        justify="left",
                    ),
                    border_style=constants.PUMAZ_COLORS["error"],
                    padding=(1, 2),
                )
            )
        except Exception as exc:  # pragma: no cover - defensive batch execution
            logging.exception("PUMAZ failed for subject %s", subject_folder)
            error_message = str(exc) or exc.__class__.__name__
            failures.append((subject_folder, error_message))
            console.print(
                Panel(
                    Text(
                        f"{emoji.emojize(':cross_mark:')} Failed subject: {subject_folder}\nReason: {error_message}",
                        style=constants.PUMAZ_COLORS["error"],
                        justify="left",
                    ),
                    border_style=constants.PUMAZ_COLORS["error"],
                    padding=(1, 2),
                )
            )

    failure_log_path = None
    if failures:
        failure_log_path = Path.cwd() / f"pumaz-failures-{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"
        with failure_log_path.open("w", encoding="utf-8") as failure_file:
            for subject_folder, reason in failures:
                failure_file.write(f"{subject_folder}\t{reason}\n")

    summary_text = Text(justify="left")
    summary_text.append(
        f"Processed {total_subjects} subject(s).\n",
        style=f"bold {constants.PUMAZ_COLORS['info']}",
    )
    summary_text.append(
        f"Successful: {total_subjects - len(failures)}\n",
        style=f"bold {constants.PUMAZ_COLORS['success']}",
    )

    if failures:
        summary_text.append(
            f"Failed: {len(failures)}\n",
            style=f"bold {constants.PUMAZ_COLORS['warning']}",
        )
        if failure_log_path is not None:
            summary_text.append(
                f"Failure log: {failure_log_path}\n",
                style=f"bold {constants.PUMAZ_COLORS['warning']}",
            )
    else:
        summary_text.append(
            "Failed: 0\n",
            style=f"bold {constants.PUMAZ_COLORS['success']}",
        )

    summary_panel = Panel(
        Align.left(summary_text),
        title=Text(
            f"{emoji.emojize(':clipboard:')} Batch Summary",
            style=f"bold {constants.PUMAZ_COLORS['secondary']}",
        ),
        border_style=constants.PUMAZ_COLORS["border"],
        padding=(1, 2),
    )
    console.print()
    console.print(summary_panel)
    return failures


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "-d",
    "--subject-directory",
    "subject_directories",
    type=click.Path(exists=True, file_okay=False, resolve_path=True, path_type=str),
    multiple=True,
    help="Directory containing PET/CT tracer folders for a subject. Repeat for batch runs.",
)
@click.option(
    "-sr",
    "--subjects-root",
    type=click.Path(exists=True, file_okay=False, resolve_path=True, path_type=str),
    default=None,
    help="Process every immediate subdirectory under this root as a subject.",
)
@click.option(
    "--verify-environment",
    is_flag=True,
    default=False,
    help="Check that required binaries are available and exit.",
)
@click.option(
    "-ir",
    "--ignore-regions",
    callback=_parse_ignore_regions,
    required=False,
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
def cli(subject_directories, subjects_root, verify_environment, ignore_regions, multiplex, custom_colors, color_map, convert_to_dicom,
        risk_analysis):
    """
    PUMA (PET Universal Multi-tracer Aligner) standardizes, registers, and multiplexes serial PET/CT studies.
    """
    logging.basicConfig(format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s', level=logging.INFO,
                        filename=datetime.now().strftime('pumaz-v.1.0.0.%H-%M-%d-%m-%Y.log'), filemode='w')
    colorama.init()

    if verify_environment:
        ready = perform_environment_check()
        raise SystemExit(0 if ready else 1)

    if color_map and not multiplex:
        raise click.UsageError("--color-map requires --multiplex.")
    if custom_colors and not multiplex:
        raise click.UsageError("--custom-colors requires --multiplex.")
    if not ignore_regions:
        raise click.UsageError("Provide at least one --ignore-regions value (use 'none' for all regions).")

    resolved_subjects = [os.path.abspath(subject) for subject in subject_directories]

    if subjects_root is not None:
        root_path = Path(subjects_root)
        discovered_subjects = sorted(child for child in root_path.iterdir() if child.is_dir())
        if not discovered_subjects:
            raise click.BadParameter(
                f"No subject directories found under '{subjects_root}'.",
                param_hint="--subjects-root",
            )
        resolved_subjects.extend(str(child.resolve()) for child in discovered_subjects)

    # Deduplicate while preserving order
    seen = set()
    ordered_subjects = []
    for subject in resolved_subjects:
        if subject not in seen:
            ordered_subjects.append(subject)
            seen.add(subject)

    if not ordered_subjects:
        raise click.UsageError("Provide at least one --subject-directory or a valid --subjects-root.")

    if len(ordered_subjects) == 1:
        run_pipeline(
            ordered_subjects[0],
            ignore_regions,
            multiplex,
            custom_colors,
            color_map,
            convert_to_dicom,
            risk_analysis,
        )
    else:
        run_batch(
            ordered_subjects,
            ignore_regions,
            multiplex,
            custom_colors,
            color_map,
            convert_to_dicom,
            risk_analysis,
        )


def main():
    cli()


if __name__ == "__main__":
    main()
