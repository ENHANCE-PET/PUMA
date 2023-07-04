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

import os
import requests
import zipfile
import logging
from rich.progress import Progress
import constants


def download(item_name, item_path, item_dict):
    """
    Downloads the item (model or binary) for the current system.
    :param item_name: The name of the item to download.
    :param item_path: The path to store the item.
    :param item_dict: The dictionary containing item info.
    """
    item_info = item_dict[item_name]
    url = item_info["url"]
    filename = os.path.join(item_path, item_info["filename"])
    directory = os.path.join(item_path, item_info["directory"])

    if not os.path.exists(directory):
        logging.info(f" Downloading {directory}")
        # show progress using rich
        response = requests.get(url, stream=True)
        total_size = int(response.headers.get("Content-Length", 0))
        chunk_size = 1024 * 10

        with Progress() as progress:
            task = progress.add_task(f"[white] Downloading {item_name}...", total=total_size)
            for chunk in response.iter_content(chunk_size=chunk_size):
                open(filename, "ab").write(chunk)
                progress.update(task, advance=chunk_size)

        # Unzip the item
        with Progress() as progress:
            with zipfile.ZipFile(filename, 'r') as zip_ref:
                total_size = sum((file.file_size for file in zip_ref.infolist()))
                task = progress.add_task(f"[white] Extracting {item_name}...", total=total_size)
                # Get the parent directory of 'directory'
                parent_directory = os.path.dirname(directory)
                for file in zip_ref.infolist():
                    zip_ref.extract(file, parent_directory)
                    extracted_size = file.file_size
                    progress.update(task, advance=extracted_size)

        logging.info(f" {os.path.basename(directory)} extracted.")

        # Delete the zip file
        os.remove(filename)
        print(f"{constants.ANSI_GREEN} {os.path.basename(directory)} - download complete. {constants.ANSI_RESET}")
        logging.info(f" {os.path.basename(directory)} - download complete.")
    else:
        print(f"{constants.ANSI_GREEN} A local instance of {os.path.basename(directory)} has been detected. "
              f"{constants.ANSI_RESET}")
        logging.info(f" A local instance of {os.path.basename(directory)} has been detected.")
