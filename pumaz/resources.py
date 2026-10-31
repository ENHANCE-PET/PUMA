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
        "url": "https://github.com/ENHANCE-PET/PUMA/releases/download/pumaz-v.1.8.10/beast-binaries-windows-x86_64.zip",
        "filename": "beast-binaries-windows-x86_64.zip",
        "directory": "beast-binaries-windows-x86_64",
        "sha256": "4b0419e401bf4e9a65c1f25f421a4301b413d3d380002794b3d637ed413363dc",
    },
    "puma-linux-x86_64": {
        "url": "https://github.com/ENHANCE-PET/PUMA/releases/download/pumaz-v.1.8.10/beast-binaries-linux-x86_64.zip",
        "filename": "beast-binaries-linux-x86_64.zip",
        "directory": "beast-binaries-linux-x86_64",
        "sha256": "41409bef70d42048bfb63dab8884f50bf856b757c149aedd61deb7031ad18dff",
    },
    "puma-linux-arm64": {
        "url": "https://github.com/ENHANCE-PET/PUMA/releases/download/pumaz-v.1.8.10/beast-binaries-linux-arm64.zip",
        "filename": "beast-binaries-linux-arm64.zip",
        "directory": "beast-binaries-linux-arm64",
        "sha256": "c81e74710169a85c125ab57bd1f406025b5a025fb5f8bb5fb7d1740882b11489",
    },
    "puma-mac-x86_64": {
        "url": "https://github.com/ENHANCE-PET/PUMA/releases/download/pumaz-v.1.8.10/beast-binaries-mac-x86_64.zip",
        "filename": "beast-binaries-mac-x86_64.zip",
        "directory": "beast-binaries-mac-x86_64",
        "sha256": "e7ecd6ab2eeb6cbc5c562adda801c12d3a3833f0bdfe8a9bc578577afc3b4659",
    },
    "puma-mac-arm64": {
        "url": "https://github.com/ENHANCE-PET/PUMA/releases/download/pumaz-v.1.8.10/beast-binaries-mac-arm64.zip",
        "filename": "beast-binaries-mac-arm64.zip",
        "directory": "beast-binaries-mac-arm64",
        "sha256": "f5985f10bf27bcd0e1ab218ec4b164e3550d19efcdb9d82c0eaf4d6781116b8a",
    },
}


def check_device() -> str:
    """
    This function checks the available device for running predictions, considering CUDA and MPS (for Apple Silicon).

    Returns:
        str: The device to run predictions on, either "cpu", "cuda", or "mps".
    """
    # Check for CUDA
    if torch.cuda.is_available():
        device_count = torch.cuda.device_count()
        print(f" CUDA is available with {device_count} GPU(s). Predictions will be run on GPU.")
        return "cuda"
    # Check for MPS (Apple Silicon) Here for the future but not compatible right now
    elif torch.backends.mps.is_available():
        print(" Apple MPS backend is available. Predictions will be run on Apple Silicon GPU.")
        return "mps"
    elif not torch.backends.mps.is_built():
        print(" MPS not available because the current PyTorch install was not built with MPS enabled.")
        return "cpu"
    else:
        print(" CUDA/MPS not available. Predictions will be run on CPU.")
        return "cpu"
