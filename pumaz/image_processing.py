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
import contextlib
import SimpleITK as sitk
import numpy as np
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
from rich.progress import track, Progress
from moosez import moose
import nibabel as nib
from pumaz.file_utilities import create_directory, move_file, remove_directory, move_files_to_directory, get_files
from halo import Halo
import time


def process_and_moose_ct_files(ct_dir: str, mask_dir: str, moose_model: str, accelerator: str):
    # Get all ct_files in the ct_dir
    ct_files = get_files(ct_dir, '*.nii*')

    with Progress() as progress_bar:
        task = progress_bar.add_task("[cyan] MOOSE-ing CT files...", total=len(ct_files))

        for ct_file in ct_files:
            base_name = os.path.basename(ct_file).split('.')[0]

            ct_file_dir = os.path.join(ct_dir, base_name)
            create_directory(ct_file_dir)
            move_file(ct_file, os.path.join(ct_file_dir, os.path.basename(ct_file)))

            mask_file_dir = os.path.join(mask_dir, base_name)
            create_directory(mask_file_dir)

            progress_bar.update(task, advance=0, description=f"[cyan] Running MOOSE on {base_name}...")

            with open(os.devnull, 'w') as devnull:
                with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
                    moose(moose_model, ct_file_dir, mask_file_dir, accelerator)

            progress_bar.update(task, advance=0, description=f"[cyan] Completed MOOSE on {base_name}, cleaning up...")

            move_files_to_directory(ct_file_dir, ct_dir)
            move_files_to_directory(mask_file_dir, mask_dir)

            remove_directory(ct_file_dir)
            remove_directory(mask_file_dir)

            progress_bar.update(task, advance=1, description=f"[cyan] Finished processing {base_name}")

            time.sleep(1)  # delay for 1 second


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
    for i, subdir in enumerate(puma_compliant_subjects):
        ct_file = glob.glob(os.path.join(subdir, 'CT*.nii*'))
        pt_file = glob.glob(os.path.join(subdir, 'PET*.nii*'))
        resliced_ct_file = os.path.join(subdir, constants.RESAMPLED_PREFIX + str(i) + '_' +
                                        os.path.basename(subdir) + '_' +
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


def change_mask_labels(mask_file: str, label_map: dict, excluded_labels: list):
    # Load the image
    img = nib.load(mask_file)

    # Get the image data (returns a numpy array)
    data = img.get_fdata()

    # Prepare labels for modification
    excluded_indices = [idx for idx, lbl in label_map.items() if lbl in excluded_labels]
    other_indices = [idx for idx, lbl in label_map.items() if lbl not in excluded_labels]

    # Set the labels
    data[np.isin(data, excluded_indices)] = 0
    data[np.isin(data, other_indices)] = 1

    # Save the modified image
    new_img = nib.Nifti1Image(data, img.affine, img.header)
    nib.save(new_img, mask_file)


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
    mask_dir = os.path.join(puma_working_dir, constants.MASK_FOLDER)
    file_utilities.create_directory(ct_dir)
    file_utilities.create_directory(pt_dir)

    index = 0
    # Move and rename files in parallel
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        for subdir in puma_compliant_subjects:
            ct_file = glob.glob(os.path.join(subdir, 'CT*.nii*'))
            resliced_ct_file = glob.glob(os.path.join(subdir, constants.RESAMPLED_PREFIX + '*CT*.nii*'))[0]
            executor.submit(copy_and_rename_file, resliced_ct_file, ct_dir, subdir)

            pt_file = glob.glob(os.path.join(subdir, 'PET*.nii*'))

            # Generate new filename with unique index
            new_pt_file = re.sub(r'PET_', f'PET_{index}_', pt_file[0])
            # rename the actual file
            os.rename(pt_file[0], new_pt_file)

            index += 1
            executor.submit(copy_and_rename_file, new_pt_file, pt_dir, subdir)

    # Run moosez to get the masks

    process_and_moose_ct_files(ct_dir, mask_dir, constants.MOOSE_MODEL, constants.ACCELERATOR)

    # remove the prefix from the mask files

    for mask_file in glob.glob(os.path.join(mask_dir, constants.MOOSE_PREFIX + '*')):
        new_mask_file = re.sub(rf'{constants.MOOSE_PREFIX}', '', mask_file)
        os.rename(mask_file, new_mask_file)
        change_mask_labels(new_mask_file, constants.MOOSE_LABEL_INDEX, ["Arms"])

    return puma_working_dir, ct_dir, pt_dir, mask_dir


class ImageRegistration:
    def __init__(self, fixed_img: str, multi_resolution_iterations: str, fixed_mask: str = None):
        self.fixed_img = fixed_img
        self.fixed_mask = fixed_mask
        self.multi_resolution_iterations = multi_resolution_iterations
        self.moving_img = None
        self.transform_files = None

    def set_moving_image(self, moving_img: str, update_transforms: bool = True):
        self.moving_img = moving_img
        if update_transforms:
            out_dir = pathlib.Path(self.moving_img).parent
            moving_img_filename = pathlib.Path(self.moving_img).name
            self.transform_files = {
                'rigid': os.path.join(out_dir, f"{moving_img_filename}_rigid.mat"),
                'affine': os.path.join(out_dir, f"{moving_img_filename}_affine.mat"),
                'warp': os.path.join(out_dir, f"{moving_img_filename}_warp.nii.gz"),
                'inverse_warp': os.path.join(out_dir, f"{moving_img_filename}_inverse_warp.nii.gz")
            }

    def rigid(self) -> str:
        mask_cmd = f"-gm {re.escape(self.fixed_mask)}" if self.fixed_mask else ""
        cmd_to_run = f"{GREEDY_PATH} -d 3 -a -i {re.escape(self.fixed_img)} {re.escape(self.moving_img)} " \
                     f"{mask_cmd} -ia-image-centers -dof 6 -o {re.escape(self.transform_files['rigid'])} " \
                     f"-n {self.multi_resolution_iterations} -m SSD"
        subprocess.run(cmd_to_run, shell=True, capture_output=True)
        logging.info(
            f"Rigid alignment: {pathlib.Path(self.moving_img).name} -> {pathlib.Path(self.fixed_img).name} | Aligned image: "
            f"moco-{pathlib.Path(self.moving_img).name} | Transform file: {pathlib.Path(self.transform_files['rigid']).name}")
        return self.transform_files['rigid']

    def affine(self) -> str:
        mask_cmd = f"-gm {re.escape(self.fixed_mask)}" if self.fixed_mask else ""
        cmd_to_run = f"{GREEDY_PATH} -d 3 -a -i {re.escape(self.fixed_img)} {re.escape(self.moving_img)} " \
                     f"{mask_cmd} -ia-image-centers -dof 12 -o {re.escape(self.transform_files['affine'])} " \
                     f"-n {self.multi_resolution_iterations} -m SSD"
        subprocess.run(cmd_to_run, shell=True, capture_output=True)
        logging.info(
            f"Affine alignment: {pathlib.Path(self.moving_img).name} -> {pathlib.Path(self.fixed_img).name} |"
            f" Aligned image: moco-{pathlib.Path(self.moving_img).name} | Transform file: {pathlib.Path(self.transform_files['affine']).name}")
        return self.transform_files['affine']

    def deformable(self) -> tuple:
        self.rigid()
        mask_cmd = f"-gm {re.escape(self.fixed_mask)}" if self.fixed_mask else ""
        cmd_to_run = f"{GREEDY_PATH} -d 3 -m SSD -i {re.escape(self.fixed_img)} {re.escape(self.moving_img)} " \
                     f"{mask_cmd} -it {re.escape(self.transform_files['rigid'])} -o {re.escape(self.transform_files['warp'])} " \
                     f"-oinv {re.escape(self.transform_files['inverse_warp'])} -sv -n {self.multi_resolution_iterations}"
        subprocess.run(cmd_to_run, shell=True, capture_output=True)
        logging.info(
            f"Deformable alignment: {pathlib.Path(self.moving_img).name} -> {pathlib.Path(self.fixed_img).name} | "
            f"Aligned image: moco-{pathlib.Path(self.moving_img).name} | "
            f"Initial alignment:{pathlib.Path(self.transform_files['rigid']).name}"
            f" | warp file: {pathlib.Path(self.transform_files['warp']).name}")
        return self.transform_files['rigid'], self.transform_files['warp'], self.transform_files['inverse_warp']

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
        if registration_type == 'rigid':
            cmd_to_run = self._build_cmd(resampled_moving_img, segmentation, resampled_seg,
                                         self.transform_files['rigid'])
        elif registration_type == 'affine':
            cmd_to_run = self._build_cmd(resampled_moving_img, segmentation, resampled_seg,
                                         self.transform_files['affine'])
        elif registration_type == 'deformable':
            cmd_to_run = self._build_cmd(resampled_moving_img, segmentation, resampled_seg,
                                         self.transform_files['warp'], self.transform_files['rigid'])
        subprocess.run(cmd_to_run, shell=True, capture_output=True)

    def _build_cmd(self, resampled_moving_img: str, segmentation: str, resampled_seg: str,
                   *transform_files: str) -> str:
        cmd = f"{GREEDY_PATH} -d 3 -rf {re.escape(self.fixed_img)} -ri LINEAR -rm " \
              f"{re.escape(self.moving_img)} {re.escape(resampled_moving_img)}"
        if segmentation and resampled_seg:
            cmd += f" -ri LABEL 0.2vox -rm {re.escape(segmentation)} {re.escape(resampled_seg)}"
        for transform_file in transform_files:
            cmd += f" -r {re.escape(transform_file)}"
        return cmd


def align(puma_working_dir: str, ct_dir: str, pt_dir: str, mask_dir: str):
    ct_files = sorted(glob.glob(os.path.join(ct_dir, '*.nii*')))

    reference_image = ct_files[0]
    fixed_mask = glob.glob(os.path.join(mask_dir, os.path.basename(reference_image).split('_')[0] + '*.nii*'))[0]
    moving_images = ct_files[1:]

    with Progress() as progress:
        task = progress.add_task("[cyan] Aligning CT and PT images to a common frame ", total=len(moving_images))

        for moving_image in moving_images:
            aligner = ImageRegistration(fixed_img=reference_image,
                                        multi_resolution_iterations=constants.MULTI_RESOLUTION_SCHEME,
                                        fixed_mask=fixed_mask)
            aligner.set_moving_image(moving_image)
            aligner.registration('deformable')
            aligner.resample(resampled_moving_img=os.path.join(puma_working_dir, constants.ALIGNED_PREFIX +
                                                               os.path.basename(moving_image)),
                             registration_type='deformable')
            progress.update(task, advance=1)
            pet_image = glob.glob(os.path.join(pt_dir, os.path.basename(moving_image).split('_')[0] + '*.nii*'))[0]
            aligner.set_moving_image(pet_image, update_transforms=False)
            resampled_pet_file = os.path.join(puma_working_dir, constants.ALIGNED_PREFIX +
                                              os.path.basename(pet_image))
            aligner.resample(resampled_moving_img=resampled_pet_file,
                             registration_type='deformable')

        # clean up transforms to a new folder
        rigid_transform_files = sorted(glob.glob(os.path.join(ct_dir, '*_rigid.mat')))
        warp_files = sorted(glob.glob(os.path.join(ct_dir, '*warp.nii.gz')))
        transforms_dir = os.path.join(puma_working_dir, constants.TRANSFORMS_FOLDER)
        file_utilities.create_directory(transforms_dir)
        # move all the warp files and rigid transform files to the transforms folder without zipping
        for rigid_transform_file in rigid_transform_files:
            file_utilities.move_file(rigid_transform_file, transforms_dir)
        for warp_file in warp_files:
            file_utilities.move_file(warp_file, transforms_dir)

        # move the aligned files to a new folder called aligned_CT, this is stored in the puma_working_dir
        aligned_ct_dir = os.path.join(puma_working_dir, constants.ALIGNED_CT_FOLDER)
        file_utilities.create_directory(aligned_ct_dir)
        # get aligned ct files using glob by looking for keyword 'aligned'
        aligned_ct_files = sorted(glob.glob(os.path.join(puma_working_dir, constants.ALIGNED_PREFIX + '*CT*.nii*')))
        for aligned_ct_file in aligned_ct_files:
            file_utilities.move_file(aligned_ct_file, aligned_ct_dir)
        # copy the reference ct file to the aligned_ct_dir and add an aligned prefix to the copied file
        file_utilities.copy_file(reference_image, os.path.join(aligned_ct_dir, constants.ALIGNED_PREFIX +
                                                               os.path.basename(reference_image)))

        # move the aligned PET files to a new folder called aligned_PET, this is stored in the puma_working_dir
        aligned_pet_dir = os.path.join(puma_working_dir, constants.ALIGNED_PET_FOLDER)
        file_utilities.create_directory(aligned_pet_dir)
        # get aligned pet files using glob by looking for keyword 'aligned'
        aligned_pet_files = sorted(
            glob.glob(os.path.join(puma_working_dir, constants.ALIGNED_PREFIX + '*PET*.nii*')))
        for aligned_pet_file in aligned_pet_files:
            file_utilities.move_file(aligned_pet_file, aligned_pet_dir)
        # copy the pet file corresponding to the reference ct file to the aligned_pet_dir and add an aligned prefix
        # to the copied file
        file_utilities.copy_file(
            glob.glob(os.path.join(pt_dir, os.path.basename(reference_image).split('_')[0] + '*.nii*'))[0],
            os.path.join(aligned_pet_dir, constants.ALIGNED_PREFIX +
                         os.path.basename(glob.glob(
                             os.path.join(pt_dir, os.path.basename(reference_image).split('_')[0] + '*.nii*'))[0])))
