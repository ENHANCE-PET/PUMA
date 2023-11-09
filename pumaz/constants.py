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
from datetime import datetime

from pumaz import file_utilities

project_root = file_utilities.get_virtual_env_root()
BINARY_PATH = os.path.join(project_root, 'bin')

# SET PATHS TO BINARIES

if file_utilities.get_system()[0] == 'windows':
    GREEDY_PATH = os.path.join(BINARY_PATH, f'greedy-{file_utilities.get_system()[0]}-{file_utilities.get_system()[1]}',
                               'greedy.exe')
elif file_utilities.get_system()[0] in ['linux', 'mac']:
    GREEDY_PATH = os.path.join(BINARY_PATH, f'greedy-{file_utilities.get_system()[0]}-{file_utilities.get_system()[1]}',
                               'greedy')
else:
    raise ValueError('Unsupported OS')


# COLOR CODES
ANSI_ORANGE = '\033[38;5;208m'
ANSI_GREEN = '\033[38;5;40m'
ANSI_VIOLET = '\033[38;5;141m'
ANSI_RESET = '\033[0m'

# EXPECTED MODALITIES

MODALITIES = ['PET', 'CT']
MODALITIES_PREFIX = ['PT_ for PET', 'CT_ for CT']

# FILE NAMES

RESAMPLED_PREFIX = 'resampled_'
ALIGNED_PREFIX = 'aligned_'
ALIGNED_PREFIX_PT = 'aligned_PT_'
ALIGNED_PREFIX_CT = 'aligned_CT_'
ALIGNED_PREFIX_MASK = 'aligned_MASK_'

# MOOSE PARAMETERS

MOOSE_MODEL_BODY = "clin_ct_body"
MOOSE_MODEL_PUMA = "clin_ct_PUMA"
MOOSE_PREFIX_BODY = 'CT_Body_'
MOOSE_PREFIX_PUMA = 'Clin_CT_PUMA_'
MOOSE_LABEL_INDEX = {
        1: "legs",
        2: "body",
        3: "head",
        4: "arms"
    }
ACCELERATOR = 'cuda'

# FOLDER NAMES

PUMA_WORKING_FOLDER = 'PUMAZ-V01' + '-' + datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
TRANSFORMS_FOLDER = 'transforms'
ALIGNED_MASK_FOLDER = 'aligned_MASK'
ALIGNED_CT_FOLDER = 'aligned_CT'
ALIGNED_PET_FOLDER = 'aligned_PT'
BODY_MASK_FOLDER = 'body_masks'
PUMA_MASK_FOLDER = 'puma_masks'
COMMON_FOV_MASK_FOLDER = 'common_fov_masks'

# HYPERPARAMETERS

MULTI_RESOLUTION_SCHEME = '100x50x25'
