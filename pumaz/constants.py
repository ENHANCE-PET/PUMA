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
# This module contains the constants that are used in the pumaz.
#
# Usage:
# The variables in this module can be imported and used in other modules within the pumaz.
#
# ----------------------------------------------------------------------------------------------------------

import os
from pumaz import file_utilities
from datetime import datetime

# Root path of the project
project_root = file_utilities.get_virtual_env_root()

# Path to the binary files within the project
BINARY_PATH = os.path.join(project_root, 'bin')

# Set the appropriate path for the Greedy binary based on the operating system
if file_utilities.get_system()[0] == 'windows':
    GREEDY_PATH = os.path.join(BINARY_PATH, f'greedy-{file_utilities.get_system()[0]}-{file_utilities.get_system()[1]}',
                               'greedy.exe')
elif file_utilities.get_system()[0] in ['linux', 'mac']:
    GREEDY_PATH = os.path.join(BINARY_PATH, f'greedy-{file_utilities.get_system()[0]}-{file_utilities.get_system()[1]}',
                               'greedy')
else:
    raise ValueError('Unsupported OS')

# ANSI color codes for terminal display
ANSI_ORANGE = '\033[38;5;208m'
ANSI_GREEN = '\033[38;5;40m'
ANSI_VIOLET = '\033[38;5;141m'
ANSI_RESET = '\033[0m'

# List of expected imaging modalities
MODALITIES = ['PET', 'CT']

# Prefixes used to denote each imaging modality
MODALITIES_PREFIX = ['PT_ for PET', 'CT_ for CT']

# Prefixes for file naming
RESAMPLED_PREFIX = 'resampled_'
ALIGNED_PREFIX = 'aligned_'

# MOOSE parameters for image registration
MOOSE_MODEL = "clin_ct_body"          # MOOSE model name
MOOSE_PREFIX = 'CT_Body_'             # Prefix for MOOSE model
MOOSE_LABEL_INDEX = {                 # Index for MOOSE labels
        1: "Legs",
        2: "Body",
        3: "Head",
        4: "Arms"
    }
ACCELERATOR = 'cuda'                 # Hardware accelerator

# Folder names for storing outputs
PUMA_WORKING_FOLDER = 'PUMAZ-V01' + '-' + datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
TRANSFORMS_FOLDER = 'transforms'
ALIGNED_CT_FOLDER = 'aligned_CT'
ALIGNED_PET_FOLDER = 'aligned_PT'
MASK_FOLDER = 'masks'

# Hyperparameters for image registration
MULTI_RESOLUTION_SCHEME = '100x25x10'
