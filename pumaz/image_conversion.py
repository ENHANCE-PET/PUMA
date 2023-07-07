#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------------------------------------------------------
# Author: Lalith Kumar Shiyam Sundar | Sebastian Gutschmayer
#
# Institution: Medical University of Vienna
# Research Group: Quantitative Imaging and Medical Physics (QIMP) Team
# Date: 07.07.2023
# Version: 1.0.0
#
# Description:
# This module handles image conversion for the pumaz.
#
# Usage:
# The functions in this module can be imported and used in other modules within the pumaz to perform image conversion.
#
# ----------------------------------------------------------------------------------------------------------------------

import os
import sys
import SimpleITK
import pydicom
from rich.progress import Progress
import dicom2nifti
from pumaz import constants


def non_nifti_to_nifti(input_path: str, output_directory: str = None) -> None:
    """
    Converts any image format known to ITK to NIFTI

    :param input_path: str, Directory OR filename to convert to nii.gz
    :param output_directory: str, optional output directory to write the image to.
    """
    subject_name = os.path.basename(os.path.dirname(input_path))
    if os.path.isdir(input_path):
        image_probe = os.listdir(input_path)[0]
        modality_tag = pydicom.read_file(os.path.join(input_path, image_probe)).Modality
        output_image_basename = f"{modality_tag}_{subject_name}.nii"

        dcm2niix(input_path, output_image_basename)
        return
    elif os.path.isfile(input_path):
        if input_path.endswith('.nii.gz') or input_path.endswith('.nii'):
            return
        output_image = SimpleITK.ReadImage(input_path)
        output_image_basename = f"{os.path.splitext(os.path.basename(input_path))[0]}.nii"
    else:
        return

    if output_directory is None:
        output_directory = os.path.dirname(input_path)
    output_image_path = os.path.join(output_directory, output_image_basename)
    SimpleITK.WriteImage(output_image, output_image_path)


def standardize_to_nifti(parent_dir: str):
    """
    Converts all images in a parent directory to NIFTI
    """
    # go through the subdirectories
    subjects = os.listdir(parent_dir)
    # get only the directories
    subjects = [subject for subject in subjects if os.path.isdir(os.path.join(parent_dir, subject))]

    with Progress() as progress:
        task = progress.add_task("[white] Processing subjects...", total=len(subjects))
        for subject in subjects:
            subject_path = os.path.join(parent_dir, subject)
            if os.path.isdir(subject_path):
                images = os.listdir(subject_path)
                for image in images:
                    if os.path.isdir(os.path.join(subject_path, image)):
                        image_path = os.path.join(subject_path, image)
                        non_nifti_to_nifti(image_path)
                    elif os.path.isfile(os.path.join(subject_path, image)):
                        image_path = os.path.join(subject_path, image)
                        non_nifti_to_nifti(image_path)
            else:
                continue
            progress.update(task, advance=1, description=f"[white] Processing {subject}...")


def dcm2niix(input_path: str, output_image_basename: str) -> None:
    """
    Converts DICOM images into Nifti images using dcm2niix
    :param input_path: Path to the folder with the dicom files to convert
    :param output_image_basename: Name of the output image
    """
    output_dir = os.path.dirname(input_path)
    output_file = os.path.join(output_dir, output_image_basename)

    dicom2nifti.dicom_series_to_nifti(input_path, output_file, reorient_nifti=True)