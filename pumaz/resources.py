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

GREEDY_BINARIES = {
    "greedy-windows-x86_64": {
        "url": "https://ucd-emic-muv.s3.us-west-2.amazonaws.com/falcon/falcon-windows-x86_64.zip",
        "filename": "falcon-windows-x86_64.zip",
        "directory": "falcon-windows-x86_64",
    },
    "greedy-linux-x86_64": {
        "url": "https://ucd-emic-muv.s3.us-west-2.amazonaws.com/falcon/falcon-linux-x86_64.zip",
        "filename": "falcon-linux-x86_64.zip",
        "directory": "falcon-linux-x86_64",
    },
    "greedy-mac-x86_64": {
        "url": "https://ucd-emic-muv.s3.us-west-2.amazonaws.com/falcon/falcon-mac-x86_64.zip",
        "filename": "falcon-mac-x86_64.zip",
        "directory": "falcon-mac-x86_64",
    },
    "greedy-mac-arm64": {
        "url": "https://ucd-emic-muv.s3.us-west-2.amazonaws.com/falcon/falcon-mac-arm64.zip",
        "filename": "falcon-mac-arm64.zip",
        "directory": "falcon-mac-arm64",
    },
}
