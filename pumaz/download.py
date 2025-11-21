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
# This module downloads the necessary binaries and models for the pumaz.
#
# Usage:
# The functions in this module can be imported and used in other modules within the pumaz to download the necessary
# binaries and models for the pumaz.
#
# ----------------------------------------------------------------------------------------------------------------------

import logging
import os
import shutil
import zipfile

import requests
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, FileSizeColumn, TransferSpeedColumn, TimeRemainingColumn
from requests import exceptions as requests_exceptions

from pumaz import constants

console = Console()


class BinaryDownloadError(RuntimeError):
    """Raised when registration binaries cannot be downloaded."""


class BinaryExtractionError(RuntimeError):
    """Raised when a downloaded archive cannot be extracted."""


def _expected_files_ready(expected_files: list[str] | None) -> bool:
    """Return True when all expected binaries exist and are executable."""
    if not expected_files:
        return False
    for path in expected_files:
        if not os.path.isfile(path):
            return False
        if not os.access(path, os.X_OK):
            return False
    return True


def download(item_name: str, item_path: str, item_dict: dict, *, expected_files: list[str] | None = None) -> str:
    """
    Downloads the item (model or binary) for the current system.

    :param item_name: The name of the item to download.
    :type item_name: str
    :param item_path: The path to store the item.
    :type item_path: str
    :param item_dict: The dictionary containing item info.
    :type item_dict: dict
    :return: The path to the downloaded item.
    :rtype: str
    :raises: None

    This function downloads the item specified by `item_name` from the URL specified in the `item_dict` dictionary. It
    shows the download progress using the `rich` library and extracts the downloaded zip file using the `zipfile`
    library. If the item has already been downloaded, it skips the download and returns the path to the local copy of
    the item.

    :Example:
        >>> download('registration_binaries', '/path/to/item', {'registration_binaries': {'url': 'http://example.com/binaries.zip', 'filename': 'binaries.zip', 'directory': 'binaries'}})
    """
    binaries_ready = _expected_files_ready(expected_files)

    if binaries_ready:
        directory_hint = os.path.dirname(expected_files[0]) if expected_files else item_path
        console.print(
            f" Registration binaries detected at {directory_hint}.",
            style=constants.PUMAZ_COLORS["success"],
        )
        logging.info(f" Registration binaries detected at {directory_hint}.")
        return os.path.join(item_path, item_name)

    try:
        item_info = item_dict[item_name]
    except KeyError as exc:
        supported = ", ".join(sorted(item_dict))
        raise BinaryDownloadError(
            f"Registration binaries are not packaged for '{item_name}'. "
            "Provide compatible binaries via PUMAZ_BINARY_PATH (see README) or run on a supported platform "
            f"({supported})."
        ) from exc

    url = item_info["url"]
    filename = os.path.join(item_path, item_info["filename"])
    directory = os.path.join(item_path, item_info["directory"])

    needs_download = not os.path.isdir(directory)

    if not needs_download and expected_files:
        # Directory exists but binaries missing or not executable -> refresh
        try:
            shutil.rmtree(directory)
            needs_download = True
        except OSError:
            needs_download = True

    if needs_download:
        # Download the item
        logging.info(f" Downloading {directory}")

        # show progress using rich
        os.makedirs(item_path, exist_ok=True)
        if os.path.exists(filename):
            try:
                os.remove(filename)
            except OSError:
                pass
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
        except requests_exceptions.RequestException as exc:
            raise BinaryDownloadError(
                f"Unable to download registration binaries from {url}. "
                "Check network access or provide the binaries manually."
            ) from exc

        total_size = int(response.headers.get("Content-Length", 0))
        chunk_size = 1024 * 10

        progress = Progress(
            TextColumn(f"[{constants.PUMAZ_COLORS['accent']}][bold]{{task.description}}"),
            BarColumn(
                bar_width=None,
                style=constants.PUMAZ_COLORS["secondary"],
                complete_style=constants.PUMAZ_COLORS["primary"],
                finished_style=constants.PUMAZ_COLORS["primary"],
                pulse_style=constants.PUMAZ_COLORS["accent"],
            ),
            TextColumn(f"[{constants.PUMAZ_COLORS['info']}]{{task.percentage:>3.0f}}%"),
            TextColumn(f"[{constants.PUMAZ_COLORS['muted']}]•"),
            FileSizeColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=console,
            expand=True,
        )

        with progress:
            task = progress.add_task("[white] Downloading system specific registration binaries", total=total_size)
            with open(filename, "wb") as binary_file:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if not chunk:
                        continue
                    binary_file.write(chunk)
                    progress.update(task, advance=len(chunk))

        # Unzip the item
        progress = Progress(  # Create new instance for extraction task
            TextColumn(f"[{constants.PUMAZ_COLORS['accent']}][bold]{{task.description}}"),
            BarColumn(
                bar_width=None,
                style=constants.PUMAZ_COLORS["secondary"],
                complete_style=constants.PUMAZ_COLORS["primary"],
                finished_style=constants.PUMAZ_COLORS["primary"],
                pulse_style=constants.PUMAZ_COLORS["accent"],
            ),
            TextColumn(f"[{constants.PUMAZ_COLORS['info']}]{{task.percentage:>3.0f}}%"),
            TextColumn(f"[{constants.PUMAZ_COLORS['muted']}]•"),
            FileSizeColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=console,
            expand=True,
        )

        try:
            with progress:
                with zipfile.ZipFile(filename, 'r') as zip_ref:
                    total_size = sum((file.file_size for file in zip_ref.infolist()))
                    task = progress.add_task("[white] Extracting system specific registration binaries",
                                             total=total_size)
                    # Get the parent directory of 'directory'
                    parent_directory = os.path.dirname(directory)
                    for file in zip_ref.infolist():
                        zip_ref.extract(file, parent_directory)
                        extracted_size = file.file_size
                        progress.update(task, advance=extracted_size)
        except (zipfile.BadZipFile, OSError) as exc:
            raise BinaryExtractionError(
                f"Failed to extract registration binaries from {filename}. "
                "The archive may be corrupted or incomplete."
            ) from exc

        logging.info(f" {os.path.basename(directory)} extracted.")

        # Delete the zip file
        try:
            os.remove(filename)
        except OSError:
            pass
        console.print(
            f" Registration binaries - download complete.",
            style=constants.PUMAZ_COLORS["success"],
        )
        logging.info(f" Registration binaries - download complete.")
    return os.path.join(item_path, item_name)
