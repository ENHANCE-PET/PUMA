#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Display-only postprocessing for aligned PUMA PET volumes."""

from __future__ import annotations

from pathlib import Path

import rich_click as click
from pumaz import constants
from pumaz import display_presets
from pumaz import image_processing
from pumaz import visualization
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.text import Text


CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}
console = Console()


def _parse_color_map(ctx, param, value):
    if value is None:
        return None

    color_map = {}
    used_colors = set()
    allowed_colors = {"R", "G", "B"}

    try:
        for pair in value.split(","):
            key, val = pair.split(":")
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
        raise click.BadParameter("Colors must be formatted as tracer:color,... (for example psma:R,fdg:G)")

    return color_map


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


def _process_aligned_pt_dir(
    aligned_pt_dir: Path,
    display_preset: str,
    color_map: dict[str, str] | None,
    display_gallery: bool,
    export_rotating_mip: bool,
    rotating_mip_frames: int,
    rotating_mip_width: int,
    rotating_mip_fps: float,
    rotating_mip_interpolation: str,
    output_name: str,
) -> dict[str, str]:
    output_image = aligned_pt_dir / output_name
    result = image_processing.multiplex(
        str(aligned_pt_dir),
        "*nii*",
        "PET",
        str(output_image),
        custom_colors=False,
        color_map=color_map,
        display_preset=display_preset,
        display_gallery=display_gallery,
        review_display_presets=False,
        rename_inputs=False,
    )

    mip_png = result.get("mip_png")
    if mip_png is None:
        mip_png = str(output_image.with_name(f"{visualization.strip_nii_suffix(output_image)}_mip.png"))
        visualization.save_mip_png(output_image, mip_png, title=f"PUMA {display_preset} MIP")

    outputs = {
        "rgb_image": result["selected"]["rgb_image"],
        "mip_png": mip_png,
        "window_report": result["selected"]["window_report"],
    }
    if display_gallery:
        outputs["gallery_png"] = result["gallery_png"]

    if export_rotating_mip:
        rotating_mip = output_image.with_name(f"{visualization.strip_nii_suffix(output_image)}_rotating-mip.mp4")
        visualization.render_rotating_mip_mp4(
            result["selected"]["rgb_image"],
            rotating_mip,
            frames=rotating_mip_frames,
            fps=rotating_mip_fps,
            width=rotating_mip_width,
            interpolation=rotating_mip_interpolation,
        )
        outputs["rotating_mip"] = str(rotating_mip)

    return outputs


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument(
    "aligned_pt_directories",
    nargs=-1,
    required=True,
    type=click.Path(exists=True, file_okay=False, resolve_path=True, path_type=Path),
)
@click.option(
    "--display-preset",
    type=click.Choice(tuple(display_presets.DISPLAY_PRESETS.keys()), case_sensitive=False),
    default="balanced",
    show_default=True,
    help="RGB display window preset to apply.",
)
@click.option(
    "-cm",
    "--color-map",
    callback=_parse_color_map,
    default=None,
    metavar="map",
    help="Set tracer:color pairs when filenames do not already carry _RED/_GREEN/_BLUE suffixes.",
)
@click.option(
    "--display-gallery",
    is_flag=True,
    default=False,
    help="Generate balanced, green-suppressed, and red-focus MIP comparison outputs.",
)
@click.option(
    "--export-rotating-mip",
    is_flag=True,
    default=False,
    help="Export a spacing-aware upright rotating MIP MP4 for the selected display preset.",
)
@click.option(
    "--rotating-mip-frames",
    type=click.IntRange(min=1),
    default=120,
    show_default=True,
    help="Number of frames for --export-rotating-mip.",
)
@click.option(
    "--rotating-mip-width",
    type=click.IntRange(min=1),
    default=1600,
    show_default=True,
    help="Output width in pixels for --export-rotating-mip.",
)
@click.option(
    "--rotating-mip-fps",
    type=click.FloatRange(min=0.1),
    default=24.0,
    show_default=True,
    help="Frames per second for --export-rotating-mip.",
)
@click.option(
    "--rotating-mip-interpolation",
    type=click.Choice(("nearest", "linear", "cubic"), case_sensitive=False),
    default="cubic",
    show_default=True,
    help="OpenCV interpolation mode for --export-rotating-mip.",
)
@click.option(
    "--output-name",
    default=constants.MULTIPLEXED_COMPOSITE_IMAGE,
    show_default=True,
    help="Output RGB NIfTI filename written inside each aligned_PT directory.",
)
def cli(
    aligned_pt_directories,
    display_preset,
    color_map,
    display_gallery,
    export_rotating_mip,
    rotating_mip_frames,
    rotating_mip_width,
    rotating_mip_fps,
    rotating_mip_interpolation,
    output_name,
):
    """Apply PUMA display presets to already aligned PET volumes without rerunning registration."""
    failures = []
    for aligned_pt_dir in aligned_pt_directories:
        try:
            outputs = _process_aligned_pt_dir(
                aligned_pt_dir,
                display_preset,
                color_map,
                display_gallery,
                export_rotating_mip,
                rotating_mip_frames,
                rotating_mip_width,
                rotating_mip_fps,
                rotating_mip_interpolation,
                output_name,
            )
            lines = [f"Aligned PET directory: {aligned_pt_dir}"]
            for label, path in outputs.items():
                lines.append(f"{label}: {path}")
            _print_panel("PUMA Display Export", lines, constants.PUMAZ_COLORS["success"])
        except Exception as exc:  # pragma: no cover - defensive batch execution
            failures.append((aligned_pt_dir, str(exc) or exc.__class__.__name__))
            _print_panel(
                "PUMA Display Export Failed",
                [f"Aligned PET directory: {aligned_pt_dir}", f"Reason: {failures[-1][1]}"],
                constants.PUMAZ_COLORS["error"],
            )

    if failures:
        raise SystemExit(1)


def main():
    cli()


if __name__ == "__main__":
    main()
