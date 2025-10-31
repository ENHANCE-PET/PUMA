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
import emoji
import pyfiglet
from pumaz import constants
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn
from rich.text import Text

try:
    from cfonts import render as cfonts_render, say as cfonts_say  # type: ignore[import-not-found]
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    cfonts_render = None
    cfonts_say = None

console = Console()


def themed_progress(*additional_columns, expand=True, transient=None, console_override=None):
    """Create a themed Progress instance using the shared color palette."""
    base_columns = [
        TextColumn(f"[{constants.PUMAZ_COLORS['text']}]{{task.description}}"),
        BarColumn(
            bar_width=None,
            style=constants.PUMAZ_COLORS["muted"],
            complete_style=constants.PUMAZ_COLORS["primary"],
            finished_style=constants.PUMAZ_COLORS["primary"],
            pulse_style=constants.PUMAZ_COLORS["info"],
        ),
        TextColumn(f"[{constants.PUMAZ_COLORS['info']}]{{task.percentage:>3.0f}}%"),
    ]
    columns = base_columns + list(additional_columns)
    resolved_transient = True if transient is None else transient
    return Progress(
        *columns,
        console=console_override or console,
        expand=expand,
        transient=resolved_transient,
    )

def logo():
    """
    Display the PUMA logo.

    :return: None
    :rtype: None
    :Example:
        >>> logo()
    """
    version = constants.PUMAZ_VERSION
    console.print()
    # add a space before the banner
    console.print()
    banner_text = f"PUMA {version}"
    if cfonts_say is not None:
        cfonts_say(
            banner_text,
            colors=constants.PUMAZ_BANNER_COLORS,
            align="center",
            font=constants.PUMAZ_BANNER_FONT,
            space=False,
        )
    elif cfonts_render is not None:
        banner = cfonts_render(
            banner_text,
            colors=constants.PUMAZ_BANNER_COLORS,
            align="center",
            font=constants.PUMAZ_BANNER_FONT,
            space=False,
        )
        banner_output = banner.get("string") if isinstance(banner, dict) else banner
        console.print(str(banner_output), markup=False)
    else:
        ascii_art = pyfiglet.figlet_format(banner_text, font="speed").rstrip()
        console.print(ascii_art, style=constants.PUMAZ_COLORS["primary"], justify="center")

    subtitle = Text(
        "PET Universal Multi-tracer Aligner. A part of the ENHANCE.PET initiative.",
        style=f"bold {constants.PUMAZ_COLORS['secondary']}",
        justify="center",
    )
    console.print(Align.center(subtitle))
    console.print()

    capability = Text(
        "One Framework. Many Tracers. Unified Insight.",
        style=constants.PUMAZ_COLORS["secondary"],
        justify="center",
    )
    console.print(Align.center(capability))
    console.print()


def citation():
    """
    Display the manuscript citation for PUMA.

    :return: None
    :rtype: None
    :Example:
        >>> citation()
    """
    citation_text = Text(justify="left")
    citation_text.append(
        "Fully Automated Image-Based Multiplexing of Serial PET/CT Imaging for Facilitating "
        "Comprehensive Disease Phenotyping\n",
        style="white",
    )
    citation_text.append(
        "Lalith Kumar Shiyam Sundar, Sebastian Gutschmayer, Manuel Pires, et al.\n",
        style="white",
    )
    citation_text.append(
        "Journal of Nuclear Medicine, September 2025, jnumed.125.269688; "
        "DOI: https://doi.org/10.2967/jnumed.125.269688",
        style="white",
    )

    title_text = Text(f"{emoji.emojize(':books:')} Citation", style=f"bold {constants.PUMAZ_COLORS['secondary']}")
    panel = Panel(
        Align.left(citation_text),
        title=title_text,
        title_align="left",
        border_style=constants.PUMAZ_CITATION_BORDER_COLOR,
        padding=(1, 2),
    )
    console.print(panel)
    console.print()


def section(title: str, icon: str = ""):
    """Render a themed section heading without a surrounding panel."""
    heading = emoji.emojize(f"{icon} {title}" if icon else title).strip()
    header_text = Text(heading, style=f"bold {constants.PUMAZ_COLORS['secondary']}", justify="left")
    accent_width = max(12, min(console.width - 4, 48))
    accent_line = Text("─" * accent_width, style=constants.PUMAZ_COLORS["muted"])
    console.print()
    console.print(header_text)
    console.print(accent_line)
    console.print()


def expectations(options_lines: list[str], subject_directory: str | None = None):
    """
    Display the expected modalities for PUMA.

    This function is used to check if the user has provided the correct set of modalities for each tracer set.

    :return: None
    :rtype: None
    :Example:
        >>> expectations()
    """
    note_text = Text(justify="left", style=constants.PUMAZ_COLORS["muted"])
    note_text.append(
        f"Expected anatomical modalities: {constants.ANATOMICAL_MODALITIES} | Number required: 1\n"
    )
    note_text.append(
        f"Expected functional modalities: {constants.FUNCTIONAL_MODALITIES} | Number required: 1\n"
    )
    note_text.append(
        f"Required prefix for non-DICOM files: {constants.MODALITIES_PREFIX}\n",
        style=constants.PUMAZ_COLORS["accent"],
    )
    note_text.append("\n")
    if subject_directory:
        note_text.append(
            f"Current subject directory: {subject_directory}\n",
            style=constants.PUMAZ_COLORS["info"],
        )
    note_text.append("Chosen arguments:\n", style=constants.PUMAZ_COLORS["accent"])
    for option in options_lines:
        note_text.append(f" • {option}\n")
    warning_message = (
        "Warning: Any subject datasets in a non-DICOM format that lack the required modalities "
        "(as indicated by the file prefix) will not be included in the analysis.\n"
        "Skipping subjects without required modalities. These datasets will be excluded from the pipeline."
    )
    note_text.append("\n")
    note_text.append(warning_message, style=f"bold {constants.PUMAZ_COLORS['warning']}")
    title_text = Text(f"{emoji.emojize(':memo:')} Note", style=f"bold {constants.PUMAZ_COLORS['secondary']}")
    note_panel = Panel(
        Align.left(note_text),
        title=title_text,
        title_align="left",
        border_style=constants.PUMAZ_CITATION_BORDER_COLOR,
        padding=(1, 2),
    )
    console.print(note_panel)
    console.print()

    logging.info(
        f"Expected anatomical modalities: {constants.ANATOMICAL_MODALITIES} | Number required: 1 | "
        f"Expected functional modalities: {constants.FUNCTIONAL_MODALITIES} | Number required: 1 | "
        f"Required prefix for non-DICOM files: {constants.MODALITIES_PREFIX}" 
    )
    logging.warning(
        "Skipping subjects without the required modalities (check file prefix). "
        "These subjects will be excluded from analysis and their data will not be used."
    )
