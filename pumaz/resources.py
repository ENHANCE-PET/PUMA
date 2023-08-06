#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------------------------------------------------------
# Author: Lalith Kumar Shiyam Sundar | Sebastian Gutschmayer
# Institution: Medical University of Vienna
# Research Group: Quantitative Imaging and Medical Physics (QIMP) Team
# Date: 04.07.2023
# Version: 0.1.0
#
# Module: binaries
#
# Description:
# Amidst the labyrinth of PUMA-Z's infrastructure, the `binaries` module serves as a beacon. This module is the cornerstone 
# of PUMA-Z's functionality, ensuring every component has the tools it needs to execute flawlessly. Like the supply chain 
# of an intricate machine, it houses the URLs and filenames of the vital binaries, making sure that other modules don't 
# run astray in search of them.
#
# Akin to a quartermaster in a grand ship, this module ensures the steady flow of essential resources. Whether a module 
# requires the Greedy binaries for Windows or Mac, the `binaries` module holds the keys. It's not just about availability; 
# it's about precision, making certain that every binary is exactly where it's supposed to be.
#
# Usage:
# Developers and modules alike, when in need of critical binaries, turn to this module. It's a straightforward endeavor. 
# By importing and invoking the contained variables and functions, one ensures that PUMA-Z's operations are fueled by 
# the exact resources they demand, enabling the seamless delivery of unparalleled medical imaging services.
#
# ----------------------------------------------------------------------------------------------------------------------


GREEDY_BINARIES = {
    "greedy-windows-x86_64": {
        "url": "https://greedy.s3.eu.cloud-object-storage.appdomain.cloud/greedy-windows-x86_64.zip",
        "filename": "greedy-windows-x86_64.zip",
        "directory": "greedy-windows-x86_64",
    },
    "greedy-linux-x86_64": {
        "url": "https://greedy.s3.eu.cloud-object-storage.appdomain.cloud/greedy-linux-x86_64.zip",
        "filename": "greedy-linux-x86_64.zip",
        "directory": "greedy-linux-x86_64",
    },
    "greedy-mac-x86_64": {
        "url": "https://greedy.s3.eu.cloud-object-storage.appdomain.cloud/greedy-mac-x86_64.zip",
        "filename": "greedy-mac-x86_64.zip",
        "directory": "greedy-mac-x86_64",
    },
    "greedy-mac-arm64": {
        "url": "https://greedy.s3.eu.cloud-object-storage.appdomain.cloud/greedy-mac-arm64.zip",
        "filename": "greedy-mac-arm64.zip",
        "directory": "greedy-mac-arm64",
    },
}

def get_greedy_binaries():
    """
    Get the URLs and filenames of the Greedy binaries for different platforms.

    Returns:
        dict: A dictionary containing the URLs and filenames of the Greedy binaries for different platforms.
    """
    return GREEDY_BINARIES
