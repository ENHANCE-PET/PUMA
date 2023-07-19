#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------------------------------------------------------
# Author: Lalith Kumar Shiyam Sundar | Sebastian Gutschmayer
#
# Institution: Medical University of Vienna
# Research Group: Quantitative Imaging and Medical Physics (QIMP) Team
# Date: 19.07.2023
# Version: 1.0.0
#
# Description:
# This module handles image processing for the pumaz.
#
# Usage:
# The functions in this module can be imported and used in other modules within the pumaz to perform image conversion.
#
# ----------------------------------------------------------------------------------------------------------------------

import SimpleITK as sitk
import glob
from pumaz import constants
from pumaz.constants import GREEDY_PATH
from mpire import WorkerPool
import multiprocessing
from rich.progress import Progress
from pumaz import file_utilities
from concurrent.futures import ThreadPoolExecutor
import os
import pathlib
import subprocess
import logging
import sys
import re
from rich.progress import track


class ImageRegistration:
    def __init__(self, fixed_img: str, moving_img: str, multi_resolution_iterations: str):
        self.fixed_img = fixed_img
        self.moving_img = moving_img
        self.multi_resolution_iterations = multi_resolution_iterations

    def rigid(self) -> str:
        out_dir = pathlib.Path(self.moving_img).parent
        moving_img_filename = pathlib.Path(self.moving_img).name
        rigid_transform_file = os.path.join(out_dir, f"{moving_img_filename}_rigid.mat")
        cmd_to_run = f"{GREEDY_PATH} -d 3 -a -i {re.escape(self.fixed_img)} {re.escape(self.moving_img)} -ia-image" \
                     f"-centers -dof 6 -o {re.escape(rigid_transform_file)} -n {self.multi_resolution_iterations} -m " \
                     f"NMI"
        subprocess.run(cmd_to_run, shell=True, capture_output=True)
        logging.info(
            f"Rigid alignment: {moving_img_filename} -> {pathlib.Path(self.fixed_img).name} | Aligned image: "
            f"moco-{moving_img_filename} | Transform file: {pathlib.Path(rigid_transform_file).name}")
        return rigid_transform_file

    def affine(self) -> str:
        out_dir = pathlib.Path(self.moving_img).parent
        moving_img_filename = pathlib.Path(self.moving_img).name
        affine_transform_file = os.path.join(out_dir, f"{moving_img_filename}_affine.mat")
        cmd_to_run = f"{GREEDY_PATH} -d 3 -a -i {re.escape(self.fixed_img)} {re.escape(self.moving_img)} -ia-image" \
                     f"-centers -dof 12 -o {re.escape(affine_transform_file)} -n {self.multi_resolution_iterations} " \
                     f"-m NMI"
        subprocess.run(cmd_to_run, shell=True, capture_output=True)
        logging.info(
            f"Affine alignment: {moving_img_filename} -> {pathlib.Path(self.fixed_img).name} |"
            f" Aligned image: mock-{moving_img_filename} | Transform file: {pathlib.Path(affine_transform_file).name}")
        return affine_transform_file

    def deformable(self) -> tuple:
        out_dir = pathlib.Path(self.moving_img).parent
        moving_img_filename = pathlib.Path(self.moving_img).name
        warp_file = os.path.join(out_dir, f"{moving_img_filename}_warp.nii.gz")
        inverse_warp_file = os.path.join(out_dir, f"{moving_img_filename}_inverse_warp.nii.gz")
        affine_transform_file = self.affine()
        cmd_to_run = f"{GREEDY_PATH} -d 3 -m NCC 2x2x2 -i {re.escape(self.fixed_img)} {re.escape(self.moving_img)} " \
                     f"-it {re.escape(affine_transform_file)} -o {re.escape(warp_file)} -oinv" \
                     f" {re.escape(inverse_warp_file)} -sv -n {self.multi_resolution_iterations}"
        subprocess.run(cmd_to_run, shell=True, capture_output=True)
        logging.info(
            f"Deformable alignment: {moving_img_filename} -> {pathlib.Path(self.fixed_img).name} | "
            f"Aligned image: moco-{moving_img_filename} | Initial alignment:{pathlib.Path(affine_transform_file).name}"
            f" | warp file: {pathlib.Path(warp_file).name}")
        return affine_transform_file, warp_file, inverse_warp_file

    def registration(self, registration_type: str) -> None:
        if registration_type == 'rigid':
            self.rigid()
        elif registration_type == 'affine':
            self.affine()
        elif registration_type == 'deformable':
            self.deformable()
        else:
            sys.exit("Registration type not supported!")

    def resample(self, resampled_moving_img: str, registration_type: str, segmentation="", resampled_seg="") -> None:
        moving_img_file = pathlib.Path(self.moving_img).name
        out_dir = pathlib.Path(self.moving_img).parent
        if registration_type == 'rigid':
            rigid_transform_file = os.path.join(out_dir, f"{moving_img_file}_rigid.mat")
            if segmentation and resampled_seg:
                cmd_to_run = f"{GREEDY_PATH} -d 3 -rf {re.escape(self.fixed_img)} -ri LINEAR -rm " \
                             f"{re.escape(self.moving_img)} {re.escape(resampled_moving_img)} -ri LABEL 0.2vox -rm " \
                             f"{re.escape(segmentation)} {re.escape(resampled_seg)} -r {re.escape(rigid_transform_file)}"
            else:
                cmd_to_run = f"{GREEDY_PATH} -d 3 -rf {re.escape(self.fixed_img)} -ri LINEAR -rm" \
                             f" {re.escape(self.moving_img)} {re.escape(resampled_moving_img)} -r" \
                             f" {re.escape(rigid_transform_file)}"
        elif registration_type == 'affine':
            affine_transform_file = os.path.join(out_dir, f"{moving_img_file}_affine.mat")
            if segmentation and resampled_seg:
                cmd_to_run = f"{GREEDY_PATH} -d 3 -rf {re.escape(self.fixed_img)} -ri LINEAR -rm " \
                             f"{re.escape(self.moving_img)} {re.escape(resampled_moving_img)} -ri LABEL 0.2vox -rm " \
                             f"{re.escape(segmentation)} {re.escape(resampled_seg)} -r {re.escape(affine_transform_file)}"
            else:
                cmd_to_run = f"{GREEDY_PATH} -d 3 -rf {re.escape(self.fixed_img)} -ri LINEAR -rm " \
                             f"{re.escape(self.moving_img)} {re.escape(resampled_moving_img)} -r" \
                             f" {re.escape(affine_transform_file)}"
        elif registration_type == 'deformable':
            warp_file = os.path.join(out_dir, f"{moving_img_file}_warp.nii.gz")
            affine_transform_file = os.path.join(out_dir, f"{moving_img_file}_affine.mat")
            if segmentation and resampled_seg:
                cmd_to_run = f"{GREEDY_PATH} -d 3 -rf {re.escape(self.fixed_img)} -ri LINEAR -rm " \
                             f"{re.escape(self.moving_img)} {re.escape(resampled_moving_img)} -ri LABEL 0.2vox -rm " \
                             f"{re.escape(segmentation)} {re.escape(resampled_seg)} -r {re.escape(warp_file)}" \
                             f" {re.escape(affine_transform_file)}"
            else:
                cmd_to_run = f"{GREEDY_PATH} -d 3 -rf {re.escape(self.fixed_img)} -ri LINEAR -rm " \
                             f"{re.escape(self.moving_img)} {re.escape(resampled_moving_img)} -r {re.escape(warp_file)}" \
                             f" {re.escape(affine_transform_file)}"
        subprocess.run(cmd_to_run, shell=True, capture_output=True)


def reslice_identity(reference_image: sitk.Image, moving_image: sitk.Image,
                     output_image_path: str = None, is_label_image: bool = False) -> sitk.Image:
    """
    Reslice an image to the same space as another image
    :param reference_image: The reference image
    :param moving_image: The image to reslice to the reference image
    :param output_image_path: Path to the resliced image
    :param is_label_image: Determines if the image is a label image. Default is False
    """
    resampler = sitk.ResampleImageFilter()
    resampler.SetReferenceImage(reference_image)

    if is_label_image:
        resampler.SetInterpolator(sitk.sitkNearestNeighbor)
    else:
        resampler.SetInterpolator(sitk.sitkLinear)

    resampled_image = resampler.Execute(moving_image)
    resampled_image = sitk.Cast(resampled_image, sitk.sitkInt32)
    if output_image_path is not None:
        sitk.WriteImage(resampled_image, output_image_path)
    return resampled_image


def prepare_reslice_tasks(puma_compliant_subjects):
    tasks = []
    for subdir in puma_compliant_subjects:
        ct_file = glob.glob(os.path.join(subdir, 'CT*.nii*'))
        pt_file = glob.glob(os.path.join(subdir, 'PET*.nii*'))
        resliced_ct_file = os.path.join(subdir, constants.RESAMPLED_PREFIX + os.path.basename(subdir) + '_' +
                                        os.path.basename(ct_file[0]))

        tasks.append((
            sitk.ReadImage(pt_file[0]),
            sitk.ReadImage(ct_file[0]),
            resliced_ct_file,
            False
        ))
    return tasks


def copy_and_rename_file(src, dst, subdir):
    file_utilities.copy_file(src, dst)
    new_file = os.path.join(dst, os.path.basename(subdir) + '_' + os.path.basename(src))
    os.rename(os.path.join(dst, os.path.basename(src)), new_file)


def preprocess(puma_compliant_subjects: list, num_workers: int = None):
    """
    Preprocesses the images in the subject directory
    :param puma_compliant_subjects: The puma compliant subjects
    :param num_workers: The number of worker processes for parallel processing
    """
    if num_workers is None:
        num_workers = multiprocessing.cpu_count()

    tasks = prepare_reslice_tasks(puma_compliant_subjects)

    # Process tasks in parallel using mpire
    with WorkerPool(n_jobs=num_workers) as pool:
        with Progress() as progress:
            task = progress.add_task("[cyan] Preprocessing PUMA compliant subjects ", total=len(tasks))

            for _ in pool.map(reslice_identity, tasks):
                progress.update(task, advance=1)

    # set puma working directory
    parent_dir = os.path.dirname(puma_compliant_subjects[0])
    puma_working_dir = os.path.join(parent_dir, constants.PUMA_WORKING_FOLDER)
    file_utilities.create_directory(puma_working_dir)

    # create CT and PET folders
    ct_dir = os.path.join(puma_working_dir, constants.MODALITIES[1])
    pt_dir = os.path.join(puma_working_dir, constants.MODALITIES[0])
    file_utilities.create_directory(ct_dir)
    file_utilities.create_directory(pt_dir)

    # Move and rename files in parallel
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        for subdir in puma_compliant_subjects:
            ct_file = glob.glob(os.path.join(subdir, 'CT*.nii*'))
            resliced_ct_file = glob.glob(os.path.join(subdir, constants.RESAMPLED_PREFIX + '*CT*.nii*'))[0]
            executor.submit(copy_and_rename_file, resliced_ct_file, ct_dir, subdir)

            pt_file = glob.glob(os.path.join(subdir, 'PET*.nii*'))
            executor.submit(copy_and_rename_file, pt_file[0], pt_dir, subdir)

    return puma_working_dir, ct_dir, pt_dir


def align(puma_working_dir: str, ct_dir: str, pt_dir: str):
    """
    Aligns the images in the subject directory
    :param puma_working_dir: The puma working directory
    :param ct_dir: The CT directory
    :param pt_dir: The PET directory
    """
    # get the ct files sorted using glob
    ct_files = sorted(glob.glob(os.path.join(ct_dir, '*.nii*')))
    # the first file will be the reference image and the rest will be the moving images
    reference_image = ct_files[0]
    moving_images = ct_files[1:]

    # align using the first CT image as the reference image
    with Progress() as progress:
        task = progress.add_task("[cyan] Aligning CT images ", total=len(moving_images))

        for moving_image in moving_images:
            aligner = ImageRegistration(fixed_img=reference_image, moving_img=moving_image,
                                        multi_resolution_iterations=constants.MULTI_RESOLUTION_SCHEME)
            aligner.registration('deformable')
            aligner.resample(resampled_moving_img=os.path.join(puma_working_dir, constants.ALIGNED_PREFIX +
                                                               os.path.basename(moving_image)),
                             registration_type='deformable')
            progress.update(task, advance=1)

    # clean up transforms to a new folder
    affine_transform_files = sorted(glob.glob(os.path.join(ct_dir, '*_affine.mat')))
    warp_files = sorted(glob.glob(os.path.join(ct_dir, '*warp.nii.gz')))
    transforms_dir = os.path.join(puma_working_dir, constants.TRANSFORMS_FOLDER)
    file_utilities.create_directory(transforms_dir)
    # move all the warp files and affine transform files to the transforms folder without zipping
    for affine_transform_file in affine_transform_files:
        file_utilities.move_file(affine_transform_file, transforms_dir)
    for warp_file in warp_files:
        file_utilities.move_file(warp_file, transforms_dir)

