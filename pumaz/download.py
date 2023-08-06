# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------------------------------------------------------
# Author: Lalith Kumar Shiyam Sundar | Sebastian Gutschmayer
# Institution: Medical University of Vienna
# Research Group: Quantitative Imaging and Medical Physics (QIMP) Team
# Date: 04.07.2023
# Version: 0.1.0
#
# Module: download
#
# Description:
# The `download` module serves a critical role in the PUMA-Z ecosystem, ensuring that users have the required 
# binaries and models at their fingertips. It automates the process of fetching the latest or necessary versions
# of these resources, sparing the user from the manual and often error-prone process of acquisition. 
# By centralizing and standardizing this process, PUMA-Z guarantees a smooth, hassle-free setup and execution 
# experience for its users.
# 
# Usage:
# Developers and users can seamlessly import and utilize the functions from this module within other components 
# of PUMA-Z. These functions ensure that every PUMA-Z operation, which requires external binaries or models, 
# gets access to the right version without any hitches, enhancing the tool's robustness and reliability.
#
# ----------------------------------------------------------------------------------------------------------------------


import logging
import os
import zipfile
import requests
from pumaz import constants
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, FileSizeColumn, TransferSpeedColumn

def download(item_name, item_path, item_dict):
    """
    Downloads the specified item (model or binary) for the current system.

    Parameters:
        item_name (str): The name of the item to download.
        item_path (str): The path to store the item.
        item_dict (dict): The dictionary containing item info.

    Returns:
        str: The absolute path to the downloaded item.
    """

    item_info = item_dict[item_name]
    url = item_info["url"]
    filename = os.path.join(item_path, item_info["filename"])
    directory = os.path.join(item_path, item_info["directory"])

    if not os.path.exists(directory):
        logging.info(f"Downloading {directory}")

        # Show download progress using rich library
        response = requests.get(url, stream=True)
        total_size = int(response.headers.get("Content-Length", 0))
        chunk_size = 1024 * 10

        console = Console()
        progress = Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=None),
            "[progress.percentage]{task.percentage:>3.0f}%",
            "•",
            FileSizeColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=console,
            expand=True
        )

        with progress:
            task = progress.add_task("[white] Downloading system specific registration binaries", total=total_size)
            for chunk in response.iter_content(chunk_size=chunk_size):
                open(filename, "ab").write(chunk)
                progress.update(task, advance=chunk_size)

        # Unzip the downloaded item
        progress = Progress(  # Create new instance for extraction task
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=None),
            "[progress.percentage]{task.percentage:>3.0f}%",
            "•",
            FileSizeColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=console,
            expand=True
        )

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

        logging.info(f"{os.path.basename(directory)} extracted.")

        # Delete the zip file after extraction
        os.remove(filename)
        print(f"{constants.ANSI_GREEN}Registration binaries - download complete.{constants.ANSI_RESET}")
        logging.info("Registration binaries - download complete.")
    else:
        print(f"{constants.ANSI_GREEN}A local instance of the system specific registration binary has been detected."
              f"{constants.ANSI_RESET}")
        logging.info("A local instance of registration binary has been detected.")

    return os.path.join(item_path, item_name)
