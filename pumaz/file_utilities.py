#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------------------------------------------------------
# Author: Lalith Kumar Shiyam Sundar | Sebastian Gutschmayer
# Institution: Medical University of Vienna
# Research Group: Quantitative Imaging and Medical Physics (QIMP) Team
# Date: 07.006.2023
# Version: 1.0.0
#
# Description:
# This module contains the functions for performing file operations for the pumaz.
#
# Usage:
# The functions in this module can be imported and used in other modules within the pumaz to perform file operations.
#
# ----------------------------------------------------------------------------------------------------------------------
import os
import glob
import shutil
import sys
from datetime import datetime
from multiprocessing import Pool


def get_virtual_env_root():
    python_exe = sys.executable
    virtual_env_root = os.path.dirname(os.path.dirname(python_exe))
    return virtual_env_root


def create_directory(directory_path: str):
    """
    Creates a directory at the specified path.
    :param directory_path: The path to the directory.
    """
    if not os.path.isdir(directory_path):
        os.makedirs(directory_path)


def get_files(directory_path: str, wildcard: str):
    """
    Gets the files from the specified directory using the wildcard.
    :param directory_path: The path to the directory.
    :param wildcard: The wildcard to be used.
    :return: The list of files.
    """
    return glob.glob(os.path.join(directory_path, wildcard))


def copy_file(file, destination):
    shutil.copy(file, destination)


def copy_files_to_destination(files: list, destination: str):
    """
    Copies the files inside the list to the destination directory in a parallel fashion.
    :param files: The list of files to be copied.
    :param destination: The path to the destination directory.
    """
    with Pool(processes=len(files)) as pool:
        pool.starmap(copy_file, [(file, destination) for file in files])


def select_files_by_modality(tracer_dirs: list, modality_tag: str) -> list:
    """
    Selects the files with the selected modality tag from the tracer directory.
    :param tracer_dirs: Path to the tracer directory.
    :param modality_tag: The modality tag to be selected.
    :return: The list of selected files.
    """
    selected_files = []
    for tracer_dir in tracer_dirs:
        files = os.listdir(tracer_dir)
        for file in files:
            if file.startswith(modality_tag) and file.endswith('.nii') or file.endswith('.nii.gz'):
                selected_files.append(os.path.join(tracer_dir, file))
    return selected_files


def organise_files_by_modality(tracer_dirs: list, modalities: list, pumaz_dir) -> None:
    """
    Organises the files by modality.
    :param tracer_dirs: The list of tracer directories
    :param modalities: The list of modalities.
    :param pumaz_dir: The path to the pumaz directory.
    """
    for modality in modalities:
        files_to_copy = select_files_by_modality(tracer_dirs, modality)
        copy_files_to_destination(files_to_copy, os.path.join(pumaz_dir, modality))
