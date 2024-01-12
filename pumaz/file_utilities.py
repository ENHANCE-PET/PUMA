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

import glob
import logging
import os
import platform
import shutil
import stat
import subprocess
import sys
from multiprocessing import Pool


def set_permissions(file_path: str, system_type: str) -> None:
    """
    Sets the permissions of a file based on the operating system.

    :param str file_path: The absolute or relative path to the file.
    :param str system_type: The type of the operating system ('windows', 'linux', 'mac').
    :return: None
    :rtype: None
    :raises FileNotFoundError: If the file specified by 'file_path' does not exist.
    :raises ValueError: If the provided operating system type is not supported.
    :raises subprocess.CalledProcessError: If the 'icacls' command fails on Windows.
    :raises PermissionError: If the 'chmod' command fails on Linux or macOS.

    **Example**

    .. code-block:: python

        >>> set_permissions('/path/to/file', 'linux')

    """
    if not os.path.exists(file_path):
        logging.error(f"File not found: {file_path}")
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        if system_type.lower() == 'windows':
            subprocess.check_call(["icacls", file_path, "/grant", "Everyone:(F)"], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        elif system_type.lower() in ['linux', 'mac']:
            os.chmod(file_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IROTH)
        else:
            logging.error(f"Unsupported operating system type provided: {system_type}")
            raise ValueError(f"Unsupported operating system type: {system_type}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to set permissions for file '{file_path}' on a Windows system. Subprocess error: {e}")
        raise e
    except PermissionError as e:
        logging.error(f"Insufficient permissions to change file permissions for '{file_path}' on a {system_type} system. Error: {e}")
        raise e
    except Exception as e:
        logging.error(f"An unexpected error occurred while setting permissions for file '{file_path}'. Error details: {e}")
        raise e


def get_virtual_env_root():
    """
    Get the root directory of the virtual environment.

    :return: The root directory of the virtual environment.
    :rtype: str
    :raises: None

    This function gets the root directory of the virtual environment by using the `sys.executable` variable to get the
    path to the Python executable, and then using `os.path.dirname` twice to get the parent directory of the executable,
    which is the root directory of the virtual environment.

    :Example:
        >>> get_virtual_env_root()
        '/path/to/virtual/environment'
    """
    python_exe = sys.executable
    virtual_env_root = os.path.dirname(os.path.dirname(python_exe))
    return virtual_env_root


def get_system():
    """
    Get the operating system and architecture.

    :return: A tuple containing the operating system and architecture.
    :rtype: tuple
    :raises: ValueError if the operating system or architecture is not supported.

    This function gets the operating system and architecture by using the `platform.system` and `platform.machine`
    functions. It converts the output of these functions to match the keys used in the rest of the code. If the operating
    system or architecture is not supported, it raises a ValueError.

    :Example:
        >>> get_system()
        ('linux', 'x86_64')
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


def create_directory(directory_path: str):
    """
    Creates a directory at the specified path.

    :param directory_path: The path to the directory.
    :type directory_path: str
    :return: None
    :rtype: None
    :raises: None

    This function creates a directory at the specified path using the `os.makedirs` function. If the directory already
    exists, it does nothing.

    :Example:
        >>> create_directory('/path/to/directory')
    """
    if not os.path.isdir(directory_path):
        os.makedirs(directory_path)


def get_files(directory_path: str, wildcard: str):
    """
    Gets the files from the specified directory using the wildcard.

    :param directory_path: The path to the directory.
    :type directory_path: str
    :param wildcard: The wildcard to be used.
    :type wildcard: str
    :return: The list of files.
    :rtype: list
    :raises: None

    This function gets the files from the specified directory using the `glob.glob` function. It joins the directory path
    and the wildcard using `os.path.join` to create the search pattern. It returns a list of file paths that match the
    search pattern.

    :Example:
        >>> get_files('/path/to/directory', '*.txt')
        ['/path/to/directory/file1.txt', '/path/to/directory/file2.txt']
    """
    return glob.glob(os.path.join(directory_path, wildcard))


def copy_file(file_path: str, destination_path: str):
    """
    Copy a file to a destination directory.

    :param file_path: The path to the file to be copied.
    :type file_path: str
    :param destination_path: The path to the destination directory.
    :type destination_path: str
    :return: None
    :rtype: None
    :raises: shutil.SameFileError if the source and destination files are the same.

    This function copies a file to a destination directory using the `shutil.copy` function. If the source and destination
    files are the same, it raises a `shutil.SameFileError`.

    :Example:
        >>> copy_file('/path/to/file', '/path/to/destination')
    """
    shutil.copy(file_path, destination_path)


def copy_files_to_destination(files: list, destination: str):
    """
    Copies the files inside the list to the destination directory in a parallel fashion.

    :param files: The list of files to be copied.
    :type files: list
    :param destination: The path to the destination directory.
    :type destination: str
    :return: None
    :rtype: None
    :raises: None

    This function copies the files inside the list to the destination directory in a parallel fashion using the
    `multiprocessing.Pool` class. It creates a process pool with the number of processes equal to the length of the files
    list, and then uses the `starmap` method to call the `copy_file` function for each file in the list, passing the file
    path and the destination directory as arguments.

    :Example:
        >>> copy_files_to_destination(['/path/to/file1', '/path/to/file2'], '/path/to/destination')
    """
    with Pool(processes=len(files)) as pool:
        pool.starmap(copy_file, [(file, destination) for file in files])


def select_files_by_modality(tracer_dirs: list, modality_tag: str) -> list:
    """
    Selects the files with the selected modality tag from the tracer directory.

    :param tracer_dirs: The list of paths to the tracer directories.
    :type tracer_dirs: list
    :param modality_tag: The modality tag to be selected.
    :type modality_tag: str
    :return: The list of selected files.
    :rtype: list
    :raises: None

    This function selects the files with the selected modality tag from the tracer directory. It iterates over each
    tracer directory in the `tracer_dirs` list, and then iterates over each file in the directory. If the file starts
    with the `modality_tag` and ends with `.nii` or `.nii.gz`, it appends the file path to the `selected_files` list.
    It returns the `selected_files` list.

    :Example:
        >>> select_files_by_modality(['/path/to/tracer/dir1', '/path/to/tracer/dir2'], 'pet')
        ['/path/to/tracer/dir1/pet_image.nii', '/path/to/tracer/dir2/pet_image.nii.gz']
    """
    selected_files = []
    for tracer_dir in tracer_dirs:
        files = os.listdir(tracer_dir)
        for file in files:
            if file.startswith(modality_tag) and (file.endswith('.nii') or file.endswith('.nii.gz')):
                selected_files.append(os.path.join(tracer_dir, file))
    return selected_files


def organise_files_by_modality(tracer_dirs: list, modalities: list, pumaz_dir: str) -> None:
    """
    Organises the files by modality.

    :param tracer_dirs: The list of paths to the tracer directories.
    :type tracer_dirs: list
    :param modalities: The list of modalities.
    :type modalities: list
    :param pumaz_dir: The path to the pumaz directory.
    :type pumaz_dir: str
    :return: None
    :rtype: None
    :raises: None

    This function organises the files by modality. It iterates over each modality in the `modalities` list, and then
    selects the files with the selected modality tag from the tracer directories using the `select_files_by_modality`
    function. It then copies the selected files to the corresponding modality directory in the `pumaz_dir` using the
    `copy_files_to_destination` function.

    :Example:
        >>> organise_files_by_modality(['/path/to/tracer/dir1', '/path/to/tracer/dir2'], ['pet', 'mri'], '/path/to/pumaz')
    """
    for modality in modalities:
        files_to_copy = select_files_by_modality(tracer_dirs, modality)
        copy_files_to_destination(files_to_copy, os.path.join(pumaz_dir, modality))


def move_file(file_path: str, destination_path: str):
    """
    Move a file to a destination directory.

    :param file_path: The path to the file to be moved.
    :type file_path: str
    :param destination_path: The path to the destination directory.
    :type destination_path: str
    :return: None
    :rtype: None
    :raises: shutil.Error if the destination file already exists.

    This function moves a file to a destination directory using the `shutil.move` function. If the destination file
    already exists, it raises a `shutil.Error`.

    :Example:
        >>> move_file('/path/to/file', '/path/to/destination')
    """
    shutil.move(file_path, destination_path)


def find_images(directory: str, pattern='*.nii*'):
    """
    Find images in a directory based on a pattern.
    :param directory: The directory to search.
    :type directory: str
    :param pattern: The pattern to search for.
    :type pattern: str
    :return: The list of images found.
    :rtype: list
    """
    return sorted(glob.glob(os.path.join(directory, pattern)))


def get_image_by_modality(directory: str, modalities: list) -> str:
    for modality in modalities:
        pattern = os.path.join(directory, f'{modality}*.nii*')
        files = glob.glob(pattern)
        if len(files) == 1:
            return files[0]


def get_modality(file_path: str, modalities: list) -> str:
    file_name = os.path.basename(file_path)
    for modality in modalities:
        if file_name.startswith(modality):
            return modality


def move_files(source_dir, destination_dir, pattern):
    """
    Move files from a source directory to a destination directory based on a pattern.
    :param source_dir: The source directory.
    :param destination_dir: The destination directory.
    :param pattern: The pattern to search for.
    :return: None
    """
    file_paths = find_images(source_dir, pattern)
    if len(file_paths) < 1:
        return

    create_directory(destination_dir)
    for file_path in file_paths:
        move_file(file_path, destination_dir)
        logging.info(f"Moved {file_path} to {destination_dir}")


def copy_reference_image(source_image, destination_dir, prefix):
    """
    Copy the reference image to the destination directory.
    :param source_image: The path to the source image.
    :param destination_dir: The path to the destination directory.
    :param prefix: The prefix to prepend to the image name.
    :return: None
    """
    destination_path = os.path.join(destination_dir, prefix + os.path.basename(source_image))
    copy_file(source_image, destination_path)
    logging.info(f"Copied {source_image} to {destination_path}")


def move_files_to_directory(src_dir: str, dest_dir: str):
    """
    Moves all files from the source directory to the destination directory.

    :param src_dir: The path to the source directory.
    :type src_dir: str
    :param dest_dir: The path to the destination directory.
    :type dest_dir: str
    :return: None
    :rtype: None
    :raises: None

    This function moves all files from the source directory to the destination directory using the `get_files` and
    `move_file` functions. It first gets a list of all files in the source directory using the `get_files` function, and
    then iterates over each file in the list, moving it to the destination directory using the `move_file` function.

    :Example:
        >>> move_files_to_directory('/path/to/source', '/path/to/destination')
    """
    src_files = get_files(src_dir, '*')
    for src_file in src_files:
        move_file(src_file, os.path.join(dest_dir, os.path.basename(src_file)))


def remove_directory(directory_path: str) -> None:
    """
    Remove a directory if it is empty.

    :param directory_path: The path to the directory to be removed.
    :type directory_path: str
    :return: None
    :rtype: None
    :raises: OSError if the directory is not empty.

    This function removes a directory only if it is empty using the `os.rmdir` function. If the directory is not empty,
    it raises an `OSError`.

    :Example:
        >>> remove_directory('/path/to/directory')
    """
    if not os.listdir(directory_path):
        os.rmdir(directory_path)
    else:
        raise OSError(f"Directory {directory_path} is not empty.")
