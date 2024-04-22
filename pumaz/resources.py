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
# This module contains the urls and filenames of the binaries that are required for the pumaz.
#
# Usage:
# The variables in this module can be imported and used in other modules within the pumaz to download the necessary
# binaries for the pumaz.
#
# ----------------------------------------------------------------------------------------------------------------------
import torch
from rich.console import Console

console = Console()

# GREEDY_BINARIES is a dictionary that contains the download information for the binaries required for the pumaz.
# Each key in the dictionary is a string that represents the name of the binary.
# The value associated with each key is another dictionary that contains the following keys:
# - "url": A string that represents the URL where the binary can be downloaded.
# - "filename": A string that represents the name of the file that will be downloaded.
# - "directory": A string that represents the name of the directory where the downloaded file will be stored.

PUMA_BINARIES = {
    "puma-windows-x86_64": {
        "url": "https://enhance-pet.s3.eu-central-1.amazonaws.com/awesome/beast-binaries-windows-x86_64.zip",
        "filename": "beast-binaries-windows-x86_64.zip",
        "directory": "beast-binaries-windows-x86_64",
    },
    "puma-linux-x86_64": {
        "url": "https://enhance-pet.s3.eu-central-1.amazonaws.com/awesome/beast-binaries-linux-x86_64.zip",
        "filename": "beast-binaries-linux-x86_64.zip",
        "directory": "beast-binaries-linux-x86_64",
    },
    "puma-mac-x86_64": {
        "url": "https://enhance-pet.s3.eu-central-1.amazonaws.com/awesome/beast-binaries-mac-x86_64.zip",
        "filename": "beast-binaries-mac-x86_64.zip",
        "directory": "beast-binaries-mac-x86_64",
    },
    "puma-mac-arm64": {
        "url": "https://enhance-pet.s3.eu-central-1.amazonaws.com/awesome/beast-binaries-mac-arm64.zip",
        "filename": "beast-binaries-mac-arm64.zip",
        "directory": "beast-binaries-mac-arm64",
    },
}


def check_device(verbose: bool = True) -> str:
    """
    This function checks the available device for running predictions, considering CUDA and MPS (for Apple Silicon),
    and provides the option to control verbosity of the print statements.

    Parameters:
        verbose (bool): If True, prints the device selection information. Defaults to True.

    Returns:
        str: The device to run predictions on, either "cpu", "cuda", or "mps".
    """
    try:
        if torch.cuda.is_available():
            device_count = torch.cuda.device_count()
            if verbose:
                console.print(f" CUDA is available with {device_count} GPU(s). Predictions will be run on GPU.",
                              style="white")
            return "cuda"
        elif torch.backends.mps.is_available():
            if verbose:
                console.print(
                    " Apple MPS backend is available. Predictions will be run on Apple Silicon GPU. (Not yet implemented)",
                              style="white")
            return "cpu"
        else:
            if verbose:
                console.print(" CUDA/MPS not available. Predictions will be run on CPU.", style="white")
            return "cpu"
    except Exception as e:
        if verbose:
            console.print(f" An error occurred while checking the device: {e}. Defaulting to CPU.")
        return "cpu"
