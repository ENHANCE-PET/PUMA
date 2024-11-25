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
    GREEDY_PATH = os.path.join(BINARY_PATH, f'beast-binaries-{file_utilities.get_system()[0]}-{file_utilities.get_system()[1]}',
                               'greedy.exe')
    C3D_PATH = os.path.join(BINARY_PATH, f'beast-binaries-{file_utilities.get_system()[0]}-{file_utilities.get_system()[1]}',
                            'c3d.exe')
elif file_utilities.get_system()[0] in ['linux', 'mac']:
    GREEDY_PATH = os.path.join(BINARY_PATH, f'beast-binaries-{file_utilities.get_system()[0]}-{file_utilities.get_system()[1]}',
                               'greedy')
    C3D_PATH = os.path.join(BINARY_PATH, f'beast-binaries-{file_utilities.get_system()[0]}-{file_utilities.get_system()[1]}',
                            'c3d')
else:
    raise ValueError('Unsupported OS')

# COLOR CODES
ANSI_ORANGE = '\033[38;5;208m'
ANSI_GREEN = '\033[38;5;40m'
ANSI_VIOLET = '\033[38;5;141m'
ANSI_RED = '\033[38;5;196m'
ANSI_RESET = '\033[0m'

# EXPECTED MODALITIES
ANATOMICAL_MODALITIES = ['CT']
FUNCTIONAL_MODALITIES = ['PT']

MODALITIES = ['PT', 'CT']
MODALITIES_PREFIX = ['PT_ for PET', 'CT_ for CT']

# FILE NAMES

RESAMPLED_PREFIX = 'resampled_'
ALIGNED_PREFIX = 'aligned_'
ALIGNED_PREFIX_PT = 'aligned_PT_'
ALIGNED_PREFIX_CT = 'aligned_CT_'
ALIGNED_PREFIX_MASK = 'aligned_MASK_'
MULTIPLEXED_COMPOSITE_IMAGE = 'RGB-composite.nii.gz'
GRAYSCALE_COMPOSITE_IMAGE = 'grayscale-composite.nii.gz'

CHANNEL_PREFIX_RED = "_RED"
CHANNEL_PREFIX_GREEN = "_GREEN"
CHANNEL_PREFIX_BLUE = "_BLUE"
CHANNEL_PREFIXES = [CHANNEL_PREFIX_RED, CHANNEL_PREFIX_GREEN, CHANNEL_PREFIX_BLUE]

# MOOSE PARAMETERS
MOOSE_MODEL_BODY = "clin_ct_body"
MOOSE_MODEL_PUMA_GPU = "clin_ct_PUMA"
MOOSE_MODEL_PUMA_CPU = "clin_ct_PUMA4"
MOOSE_PREFIX_BODY = 'clin_CT_body_segmentation_'
MOOSE_PREFIX_PUMA_GPU = 'clin_CT_PUMA_segmentation_'
MOOSE_PREFIX_PUMA_CPU = 'clin_CT_PUMA4_segmentation_'
MOOSE_LABEL_INDEX = {
    1: "legs",
    2: "body",
    3: "head",
    4: "arms"
}
MOOSE_FILLER_LABEL = 24

# FOLDER NAMES

PUMA_WORKING_FOLDER = 'PUMAZ-v1' + '-' + datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
TRANSFORMS_FOLDER = 'transforms'
ALIGNED_MASK_FOLDER = 'aligned_MASK'
ALIGNED_CT_FOLDER = 'aligned_CT'
ALIGNED_PET_FOLDER = 'aligned_PT'
BODY_MASK_FOLDER = 'body_masks'
PUMA_MASK_FOLDER = 'puma_masks'
COMMON_FOV_MASK_FOLDER = 'common_fov_masks'
SEGMENTATION_FOLDER = 'segmentation'
DICOM_FOLDER = 'dicom'

# HYPERPARAMETERS

MULTI_RESOLUTION_SCHEME = '100x50x25'

# RGB LINEAR TRANSFORMATION PARAMETERS TO GRAYSCALE BASED ON IMAGEMAGICK FORMULA

RED_WEIGHT = 0.2989
GREEN_WEIGHT = 0.5870
BLUE_WEIGHT = 0.1140

# LIONZ PARAMETERS

LIONZ_MODEL = "mpx"
LIONZ_PREFIX = "PT_"
LIONZ_OUTPUT_DIR = "seg_output"

# DICOM DESCRIPTIONS

DESCRIPTION = 'Processed-by-PUMA-AND-DICOM-conversion-by-nifti2dicom'

PUMA_LABELS = {
    "background": 0,
    "Spleen": 1,
    "Kidneys": 2,
    "Gallbladder": 3,
    "Liver": 4,
    "Stomach": 5,
    "Pancreas": 6,
    "Adrenal_glands": 7,
    "Lungs": 8,
    "Heart_myocardium": 9,
    "Heart_atrium_left": 10,
    "Heart_ventricle_left": 11,
    "Heart_atrium_right": 12,
    "Heart_ventricle_right": 13,
    "Pulmonary_artery": 14,
    "Aorta": 15,
    "Inferior_vena_cava": 16,
    "Esophagus": 17,
    "Trachea": 18,
    "Digestive": 19,
    "Brain": 20,
    "Skeleton": 21,
    "Muscles": 22,
    "Bladder": 23,
    "filler": 24
}
