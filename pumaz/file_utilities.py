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
import platform
from multiprocessing import Pool
import stat
import subprocess


def set_permissions(file_path: str, system_type: str) -> None:
    
    """
    Set permissions on the specified file based on the system type.

    For Windows systems, this grants full access to "Everyone".
    For Linux and Mac systems, it provides read, write, and execute permissions to 
    the owner and read permission to others.

    Parameters:
    - file_path (str): Path to the file whose permissions need to be set.
    - system_type (str): The operating system type (e.g., "windows", "linux", "mac").

    Raises:
    - ValueError: If the provided system_type is unsupported.
    """
    
    if system_type == "windows":
        subprocess.check_call(["icacls", file_path, "/grant", "Everyone:(F)"])
    elif system_type in ["linux", "mac"]:
        os.chmod(file_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IROTH)  # equivalent to 'chmod u+x'
    else:
        raise ValueError("Unsupported OS")


def get_virtual_env_root() -> str:
    
    """
    Get the root directory of the current Python virtual environment.

    Returns:
    - str: Path to the root of the current virtual environment.
    """
    
    python_exe = sys.executable
    virtual_env_root = os.path.dirname(os.path.dirname(python_exe))
    return virtual_env_root


def get_system() -> Tuple[str, str]:
    """
    Identify the operating system and its architecture.

    Returns:
    - Tuple[str, str]: A tuple containing the system type (e.g., "mac", "windows", "linux")
                       and the architecture (e.g., "x86_64", "arm64").

    Raises:
    - ValueError: If the detected system type or architecture is unsupported.
    """
    
    system = platform.system().lower()
    architecture = platform.machine().lower()

    # Convert system output to match your keys
    if system == "darwin":
        system = "mac"
    elif system == "windows":
        system = "windows"
    elif system == "linux":
        system = "linux"
    else:
        raise ValueError("Unsupported OS type")

    # Convert architecture output to match your keys
    if architecture in ["x86_64", "amd64"]:
        architecture = "x86_64"
    elif "arm" in architecture:
        architecture = "arm64"
    else:
        raise ValueError("Unsupported architecture")

    return system, architecture


def create_directory(directory_path: str) -> None:
    """
    Create a directory at the specified path if it doesn't exist.

    Parameters:
    - directory_path (str): The path where the directory should be created.
    """
    if not os.path.isdir(directory_path):
        os.makedirs(directory_path)


def get_files(directory_path: str, wildcard: str) -> List[str]:
    """
    Retrieve a list of files from the specified directory that match the given wildcard pattern.

    Parameters:
    - directory_path (str): The directory from which files should be retrieved.
    - wildcard (str): A wildcard pattern to match filenames against.

    Returns:
    - List[str]: A list of file paths that match the wildcard pattern.
    """
    return glob.glob(os.path.join(directory_path, wildcard))


def copy_file(file: str, destination: str) -> None:
    """
    Copy a file to the specified destination.

    Parameters:
    - file (str): Path to the source file.
    - destination (str): Path to the destination.
    """
    shutil.copy(file, destination)


def copy_files_to_destination(files: List[str], destination: str) -> None:
    """
    Copy multiple files to a specified destination directory in parallel.

    Parameters:
    - files (List[str]): A list of file paths to be copied.
    - destination (str): Destination directory path.
    """
    with Pool(processes=len(files)) as pool:
        pool.starmap(copy_file, [(file, destination) for file in files])


def select_files_by_modality(tracer_dirs: List[str], modality_tag: str) -> List[str]:
    """
    Select and retrieve files with the specified modality tag from a list of tracer directories.

    Parameters:
    - tracer_dirs (List[str]): A list of directories where tracer files are located.
    - modality_tag (str): The modality tag used to filter files.

    Returns:
    - List[str]: A list of selected file paths with the specified modality tag.
    """
    selected_files = []
    for tracer_dir in tracer_dirs:
        files = os.listdir(tracer_dir)
        for file in files:
            if file.startswith(modality_tag) and file.endswith('.nii') or file.endswith('.nii.gz'):
                selected_files.append(os.path.join(tracer_dir, file))
    return selected_files


def organise_files_by_modality(tracer_dirs: List[str], modalities: List[str], pumaz_dir: str) -> None:
    """
    Organize and copy files by modality, segregating them based on specified modalities.

    Parameters:
    - tracer_dirs (List[str]): A list of directories where tracer files are located.
    - modalities (List[str]): A list of modality tags to be used for segregation.
    - pumaz_dir (str): The target directory where files should be copied and organized.
    """
    for modality in modalities:
        files_to_copy = select_files_by_modality(tracer_dirs, modality)
        copy_files_to_destination(files_to_copy, os.path.join(pumaz_dir, modality))


def move_file(file: str, destination: str) -> None:
    """
    Move a file to the specified destination.

    Parameters:
    - file (str): Path to the source file.
    - destination (str): Path to the destination.
    """
    shutil.move(file, destination)


def move_files_to_directory(src_dir: str, dest_dir: str) -> None:
    """
    Move all files from a source directory to a destination directory.

    Parameters:
    - src_dir (str): Source directory containing the files to be moved.
    - dest_dir (str): Destination directory where files will be moved.
    """
    src_files = get_files(src_dir, '*')
    for src_file in src_files:
        move_file(src_file, os.path.join(dest_dir, os.path.basename(src_file)))


def remove_directory(directory_path: str) -> None:
    """
    Remove a directory if it is empty.

    Parameters:
    - directory_path (str): Path to the directory to be removed.
    """
    # Remove the directory only if it is empty
    if not os.listdir(directory_path):
        os.rmdir(directory_path)
