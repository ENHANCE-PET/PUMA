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
import glob
import logging
import multiprocessing
import os
import pathlib
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import GPUtil
import SimpleITK as sitk
import nibabel as nib
import numpy as np
import psutil
from lionz import lion
from moosez import moose
from mpire import WorkerPool
from pumaz import constants
from pumaz import file_utilities
from pumaz.constants import (GREEDY_PATH, C3D_PATH, ANATOMICAL_MODALITIES, FUNCTIONAL_MODALITIES, RED_WEIGHT,
                             GREEN_WEIGHT, BLUE_WEIGHT, LIONZ_MODEL, MOOSE_FILLER_LABEL)
from pumaz.file_utilities import (create_directory, move_file, remove_directory, move_files_to_directory, get_files,
                                  copy_reference_image, move_files, find_images, get_image_by_modality, get_modality)
from pumaz.resources import check_device
from rich.console import Console
from rich.progress import Progress, BarColumn, TimeElapsedColumn
from rich.table import Table


def process_and_moose_ct_files(ct_dir: str, mask_dir: str, moose_model: str, accelerator: str) -> None:
    """
    Process CT files using the MOOSE model with the specified accelerator.

    This function takes a directory of CT files and applies the MOOSE model to them. The results are saved
    in the specified mask directory. It is designed to work with a specific accelerator, such as a CPU or GPU.

    :param ct_dir: The directory containing the CT files.
    :type ct_dir: str
    :param mask_dir: The directory where the MOOSE masks should be saved.
    :type mask_dir: str
    :param moose_model: The path to the MOOSE model file.
    :type moose_model: str
    :param accelerator: The type of accelerator to use ('cpu' or 'gpu').
    :type accelerator: str
    """
    ct_files = get_files(ct_dir, '*.nii*')

    with Progress(
            "[progress.description]{task.description}",
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
            "[{task.completed}/{task.total}]",
            "[white]• Time elapsed:",  # Making static text white
            TimeElapsedColumn(),
            "[white]• CPU Load:",  # Static text in white
            "[cyan]{task.fields[cpu]}%",  # Dynamic content in cyan
            "[white]• Memory Load:",  # Static text in white
            "[cyan]{task.fields[memory]}%",  # Dynamic content in cyan
            "[white]• GPU Load:",  # Static text in white
            "[cyan]{task.fields[gpu]}%",  # Dynamic content in cyan
            expand=False
    ) as progress:
        task_description = f"[white] MOOSE-ing CT files | Model: {moose_model} | Accelerator: {accelerator}"
        task = progress.add_task(task_description, total=len(ct_files), cpu="0", memory="0", gpu="N/A")

        for ct_file in ct_files:
            base_name = os.path.basename(ct_file).split('.')[0]
            ct_file_dir = os.path.join(ct_dir, base_name)
            create_directory(ct_file_dir)
            move_file(ct_file, os.path.join(ct_file_dir, os.path.basename(ct_file)))

            mask_file_dir = os.path.join(mask_dir, base_name)
            create_directory(mask_file_dir)

            # Redirect moose output to null to avoid cluttering the console
            with open(os.devnull, 'w') as devnull:
                with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
                    moose(moose_model, ct_file_dir, mask_file_dir, accelerator)

            # Clean up intermediate directories and move files back
            move_files_to_directory(ct_file_dir, ct_dir)
            move_files_to_directory(mask_file_dir, mask_dir)
            remove_directory(ct_file_dir)
            remove_directory(mask_file_dir)

            # Update the progress bar with system loads after each file is processed
            cpu_load = psutil.cpu_percent(interval=None)
            memory_load = psutil.virtual_memory().percent
            gpus = GPUtil.getGPUs()
            gpu_load = f"{gpus[0].load * 100:.1f}" if gpus else "N/A"

            progress.update(task, advance=1, refresh=True,
                            cpu=f"{cpu_load}", memory=f"{memory_load}", gpu=gpu_load)


def reslice_identity(reference_image: sitk.Image, moving_image: sitk.Image,
                     output_image_path: str = None, is_label_image: bool = False,
                     align_centers: bool = False) -> sitk.Image:
    """
    Reslice an image to the same space as another image.

    :param reference_image: The reference image.
    :type reference_image: sitk.Image
    :param moving_image: The image to reslice to the reference image.
    :type moving_image: sitk.Image
    :param output_image_path: Path to the resliced image.
    :type output_image_path: str
    :param is_label_image: Determines if the image is a label image. Default is False.
    :type is_label_image: bool
    :param align_centers: Determines if the images should be aligned by their centers. Default is False.
    :type align_centers: bool
    :return: The resliced image.
    :rtype: sitk.Image
    :Example:
        >>> reference_image = sitk.ReadImage('/path/to/reference_image.nii.gz')
        >>> moving_image = sitk.ReadImage('/path/to/moving_image.nii.gz')
        >>> reslice_identity(reference_image, moving_image, '/path/to/output_image.nii.gz')
    """
    resampler = sitk.ResampleImageFilter()
    resampler.SetReferenceImage(reference_image)

    if is_label_image:
        resampler.SetInterpolator(sitk.sitkNearestNeighbor)
    else:
        resampler.SetInterpolator(sitk.sitkLinear)

    if align_centers:
        if (reference_image.GetSize() != moving_image.GetSize() or
                reference_image.GetSpacing() != moving_image.GetSpacing() or
                reference_image.GetOrigin() != moving_image.GetOrigin()):
            center_transform = sitk.CenteredTransformInitializer(reference_image, moving_image,
                                                                 sitk.Euler3DTransform(),
                                                                 sitk.CenteredTransformInitializerFilter.GEOMETRY)
            resampler.SetTransform(center_transform)

    resampled_image = resampler.Execute(moving_image)
    resampled_image = sitk.Cast(resampled_image, sitk.sitkInt32)

    if output_image_path is not None:
        sitk.WriteImage(resampled_image, output_image_path)

    return resampled_image


def prepare_reslice_tasks(puma_compliant_subjects):
    """
    Prepare a list of reslicing tasks for a set of PUMA-compliant subjects.

    :param puma_compliant_subjects: A list of directories containing PUMA-compliant subject data.
    :type puma_compliant_subjects: list
    :return: A list of tuples representing reslicing tasks.
    :rtype: list
    :Example:
        >>> puma_compliant_subjects = ['/path/to/subject1', '/path/to/subject2']
        >>> prepare_reslice_tasks(puma_compliant_subjects)
    """
    tasks = []
    for i, subdir in enumerate(puma_compliant_subjects):
        ct_file = get_image_by_modality(subdir, ANATOMICAL_MODALITIES)
        pt_file = get_image_by_modality(subdir, FUNCTIONAL_MODALITIES)
        resliced_ct_file = os.path.join(subdir, constants.RESAMPLED_PREFIX + str(i) + '_' +
                                        os.path.basename(subdir) + '_' + os.path.basename(ct_file))

        tasks.append((sitk.ReadImage(pt_file), sitk.ReadImage(ct_file), resliced_ct_file, False, False))
    return tasks


def copy_and_rename_file(src: str, dst: str, subdir: str) -> None:
    """
    Copy a file from the source directory to the destination directory and rename it.

    :param src: The path to the source file.
    :type src: str
    :param dst: The path to the destination directory.
    :type dst: str
    :param subdir: The name of the subdirectory containing the file.
    :type subdir: str
    :return: None
    :rtype: None
    :Example:
        >>> copy_and_rename_file('/path/to/src/file.nii.gz', '/path/to/dst', 'subdir')
    """
    file_utilities.copy_file(src, dst)
    new_file = os.path.join(dst, os.path.basename(subdir) + '_' + os.path.basename(src))
    os.rename(os.path.join(dst, os.path.basename(src)), new_file)


def change_mask_labels(mask_file: str, label_map: dict, excluded_labels: list):
    """
    Change the labels of a mask image.

    :param mask_file: The path to the mask image file.
    :type mask_file: str
    :param label_map: A dictionary mapping label indices to label names.
    :type label_map: dict
    :param excluded_labels: A list of label names to exclude from the mask.
    :type excluded_labels: list
    :return: None
    :rtype: None
    :Example:
        >>> label_map = {0: 'background', 1: 'tumor', 2: 'necrosis'}
        >>> excluded_labels = ['necrosis']
        >>> change_mask_labels('/path/to/mask.nii.gz', label_map, excluded_labels)
    """
    # Load the image
    img = nib.load(mask_file)

    # Get the image data (returns a numpy array)
    data = img.get_fdata()

    if 'none' in excluded_labels:
        # If 'none' is in the list, set all non-zero regions to 1
        data = np.where(data != 0, 1, data)
    else:
        # Prepare labels for modification
        excluded_indices = [idx for idx, lbl in label_map.items() if lbl in excluded_labels]
        other_indices = [idx for idx, lbl in label_map.items() if lbl not in excluded_labels]

        # Set the labels
        data[np.isin(data, excluded_indices)] = 0
        data[np.isin(data, other_indices)] = 1

    # Save the modified image
    data = data.astype(np.int16)
    new_img = nib.Nifti1Image(data, img.affine, img.header)
    nib.save(new_img, mask_file)


def preprocess(puma_compliant_subjects: list, regions_to_ignore: list, num_workers: int = None) -> tuple:
    """
    Preprocesses the images in the subject directory.

    :param puma_compliant_subjects: A list of paths to PUMA compliant subjects.
    :type puma_compliant_subjects: list
    :param regions_to_ignore: A list of regions to ignore during registration.
    :type regions_to_ignore: list
    :param num_workers: The number of worker processes for parallel processing.
    :type num_workers: int, optional
    :return: A tuple containing the paths to the PUMA working directory, CT directory, PET directory, and mask directory.
    :rtype: tuple
    :Example:
        >>> puma_compliant_subjects = ['/path/to/subject1', '/path/to/subject2']
        >>> regions_to_ignore = ['region1', 'region2']
        >>> preprocess(puma_compliant_subjects, regions_to_ignore)
        ('/path/to/puma_working_dir', '/path/to/ct_dir', '/path/to/pt_dir', '/path/to/body_mask_dir')
    """
    if num_workers is None:
        num_workers = multiprocessing.cpu_count()

    tasks = prepare_reslice_tasks(puma_compliant_subjects)

    # Process tasks in parallel using mpire
    with WorkerPool(n_jobs=num_workers) as pool:
        with Progress() as progress:
            task = progress.add_task("[white] Preprocessing PUMA compliant subjects ", total=len(tasks))

            for _ in pool.map(reslice_identity, tasks):
                progress.update(task, advance=1)

    # set puma working directory
    parent_dir = os.path.dirname(puma_compliant_subjects[0])
    puma_working_dir = os.path.join(parent_dir, constants.PUMA_WORKING_FOLDER)
    file_utilities.create_directory(puma_working_dir)

    # create CT and PET folders
    ct_dir = os.path.join(puma_working_dir, constants.MODALITIES[1])
    pt_dir = os.path.join(puma_working_dir, constants.MODALITIES[0])
    body_mask_dir = os.path.join(puma_working_dir, constants.BODY_MASK_FOLDER)
    puma_mask_dir = os.path.join(puma_working_dir, constants.PUMA_MASK_FOLDER)
    file_utilities.create_directory(ct_dir)
    file_utilities.create_directory(pt_dir)

    # Move and rename files in parallel
    index = 0
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        for subdir in puma_compliant_subjects:
            resliced_ct_file = glob.glob(os.path.join(subdir, constants.RESAMPLED_PREFIX + '*CT*.nii*'))[0]
            executor.submit(copy_and_rename_file, resliced_ct_file, ct_dir, subdir)

            pt_file = get_image_by_modality(subdir, FUNCTIONAL_MODALITIES)

            # Generate new filename with unique index
            modality = get_modality(pt_file, FUNCTIONAL_MODALITIES)
            new_pt_file = re.sub(f'{modality}_', f'{modality}_{index}_', pt_file)
            # rename the actual file
            os.rename(pt_file, new_pt_file)

            index += 1
            executor.submit(copy_and_rename_file, new_pt_file, pt_dir, subdir)

    # Run moosez to get the masks
    accelerator = check_device()

    # if the accelerator is a GPU, use the MOOSE PUMA model for the GPU or the CPU model otherwise
    if accelerator == 'cuda':
        moose_model_puma = constants.MOOSE_MODEL_PUMA_GPU
        moose_prefix_puma = constants.MOOSE_PREFIX_PUMA_GPU
    else:
        moose_model_puma = constants.MOOSE_MODEL_PUMA_CPU
        moose_prefix_puma = constants.MOOSE_PREFIX_PUMA_CPU

    process_and_moose_ct_files(ct_dir, body_mask_dir, constants.MOOSE_MODEL_BODY, accelerator)
    process_and_moose_ct_files(ct_dir, puma_mask_dir, moose_model_puma, accelerator)

    # Remove the body regions that are not relevant for registration

    body_mask_files = glob.glob(os.path.join(body_mask_dir, constants.MOOSE_PREFIX_BODY + '*nii*'))

    for mask_file in body_mask_files:
        new_mask_file = re.sub(rf'{constants.MOOSE_PREFIX_BODY}', '', mask_file)
        os.rename(mask_file, new_mask_file)
        change_mask_labels(new_mask_file, constants.MOOSE_LABEL_INDEX, regions_to_ignore)

    puma_mask_files = glob.glob(os.path.join(puma_mask_dir, moose_prefix_puma + '*nii*'))
    for puma_mask_file in puma_mask_files:
        new_mask_file = re.sub(rf'{moose_prefix_puma}', '', puma_mask_file)
        os.rename(puma_mask_file, new_mask_file)
        apply_mask(new_mask_file, os.path.join(body_mask_dir, os.path.basename(new_mask_file)), new_mask_file)
        update_multilabel_mask(new_mask_file, os.path.join(body_mask_dir, os.path.basename(new_mask_file)),
                               new_mask_file)

    return puma_working_dir, ct_dir, pt_dir, puma_mask_dir


def update_multilabel_mask(multilabel_mask_path: str, body_mask_path: str, output_path: str) -> None:
    """
    Updates a multilabel mask by removing a specific label, converting to binary, and filling in gaps
    from a binary body mask. The gaps are filled with a specified intensity label.

    Args:
    - multilabel_mask_path (str): Path to the multilabel mask file.
    - body_mask_path (str): Path to the body mask file.
    - output_path (str): Path where the updated mask will be saved.

    Returns:
    - None
    """
    # Load the masks
    multilabel_mask = sitk.ReadImage(multilabel_mask_path, sitk.sitkUInt8)
    body_mask = sitk.ReadImage(body_mask_path, sitk.sitkUInt8)

    # Subtract the binary PUMA mask from the binary body mask
    binary_body_mask = body_mask > 0
    remaining_mask = binary_body_mask - (multilabel_mask > 0)

    # Scale the remaining mask with the filler label intensity
    scaled_remaining_mask = remaining_mask * MOOSE_FILLER_LABEL

    # Combine the multilabel mask with no filler label and the scaled remaining mask
    final_mask = sitk.Add(multilabel_mask, scaled_remaining_mask)

    # Write the resulting mask to the output path
    sitk.WriteImage(final_mask, output_path)




class ImageRegistration:
    """
    A class for performing image registration using the GREEDY algorithm.

    :param fixed_img: The path to the fixed image.
    :type fixed_img: str
    :param multi_resolution_iterations: The number of multi-resolution iterations to perform.
    :type multi_resolution_iterations: str
    :param fixed_mask: The path to the fixed mask (optional).
    :type fixed_mask: str
    """

    def __init__(self, fixed_img: str, multi_resolution_iterations: str, fixed_mask: str = None,
                 moving_mask: str = None):
        self.fixed_img = fixed_img
        self.fixed_mask = fixed_mask
        self.moving_mask = moving_mask
        self.multi_resolution_iterations = multi_resolution_iterations
        self.moving_img = None
        self.transform_files = None

    def set_moving_image(self, moving_img: str, update_transforms: bool = True):
        """
        Set the moving image and update the transform files.

        :param moving_img: The path to the moving image.
        :type moving_img: str
        :param update_transforms: Whether to update the transform files (default is True).
        :type update_transforms: bool
        """
        self.moving_img = moving_img
        if update_transforms:
            out_dir = pathlib.Path(self.moving_img).parent
            moving_img_filename = pathlib.Path(self.moving_img).name
            self.transform_files = {
                'moments': os.path.join(out_dir, f"{moving_img_filename}_moment.mat"),
                'rigid': os.path.join(out_dir, f"{moving_img_filename}_rigid.mat"),
                'affine': os.path.join(out_dir, f"{moving_img_filename}_affine.mat"),
                'warp': os.path.join(out_dir, f"{moving_img_filename}_warp.nii.gz"),
                'inverse_warp': os.path.join(out_dir, f"{moving_img_filename}_inverse_warp.nii.gz")
            }

    def rigid(self) -> str:
        """
        Perform rigid alignment.

        :return: The path to the rigid transform file.
        :rtype: str
        """
        mask_options = {'-gm': self.fixed_mask, '-mm': self.moving_mask}
        combined_mask_cmd = " ".join(f"{key} {re.escape(value)}" for key, value in mask_options.items() if value)

        # Initialize the command with moments 1 <center of mass>

        cmd_to_run = f"{GREEDY_PATH} -d 3 -i " \
                     fr"{self.fixed_img} {self.moving_img} " \
                     f"{combined_mask_cmd} -moments 1 -o " \
                     fr"{self.transform_files['moments']} "
        subprocess.run(cmd_to_run, shell=True, capture_output=True)

        cmd_to_run = f"{GREEDY_PATH} -d 3 -a -i " \
                     fr"{self.fixed_img} {self.moving_img} " \
                     f"{combined_mask_cmd} -ia {self.transform_files['moments']} -dof 6 -o " \
                     fr"{self.transform_files['rigid']} " \
                     f"-n {self.multi_resolution_iterations} -m SSD"
        subprocess.run(cmd_to_run, shell=True, capture_output=True)

        logging.info(
            f"Rigid alignment: {pathlib.Path(self.moving_img).name} -> {pathlib.Path(self.fixed_img).name} | Aligned image: "
            f"moco-{pathlib.Path(self.moving_img).name} | Transform file: {pathlib.Path(self.transform_files['rigid']).name}")
        return self.transform_files['rigid']

    def affine(self) -> str:
        """
        Perform affine alignment.

        :return: The path to the affine transform file.
        :rtype: str
        """
        mask_options = {'-gm': self.fixed_mask, '-mm': self.moving_mask}
        combined_mask_cmd = " ".join(f"{key} {re.escape(value)}" for key, value in mask_options.items() if value)

        # Initialize the command with moments 1 <center of mass>

        cmd_to_run = f"{GREEDY_PATH} -d 3 -i " \
                     fr"{self.fixed_img} {self.moving_img} " \
                     f"{combined_mask_cmd} -moments 1 -o " \
                     fr"{self.transform_files['moments']} "

        subprocess.run(cmd_to_run, shell=True, capture_output=True)

        cmd_to_run = f"{GREEDY_PATH} -d 3 -a -i " \
                     fr"{self.fixed_img} {self.moving_img} " \
                     f"{combined_mask_cmd} -ia {self.transform_files['moments']} -dof 12 -o " \
                     fr"{self.transform_files['affine']} " \
                     f"-n {self.multi_resolution_iterations} -m SSD"
        subprocess.run(cmd_to_run, shell=True, capture_output=True)

        logging.info(
            f"Affine alignment: {pathlib.Path(self.moving_img).name} -> {pathlib.Path(self.fixed_img).name} |"
            f" Aligned image: moco-{pathlib.Path(self.moving_img).name} | Transform file: {pathlib.Path(self.transform_files['affine']).name}")
        return self.transform_files['affine']

    def deformable(self) -> tuple:
        """
        Perform deformable alignment.

        :return: A tuple containing the paths to the affine, warp, and inverse warp transform files.
        :rtype: tuple
        """
        self.affine()
        mask_options = {'-gm': self.fixed_mask, '-mm': self.moving_mask}
        combined_mask_cmd = " ".join(f"{key} {re.escape(value)}" for key, value in mask_options.items() if value)

        cmd_to_run = f"{GREEDY_PATH} -d 3 -m SSD -i " \
                     fr"{self.fixed_img} {self.moving_img} " \
                     f"{combined_mask_cmd} -it " \
                     fr"{self.transform_files['affine']} " \
                     f"-o " \
                     fr"{self.transform_files['warp']} -oinv {self.transform_files['inverse_warp']} " \
                     f"-sv -n {self.multi_resolution_iterations}"

        subprocess.run(cmd_to_run, shell=True, capture_output=True)
        logging.info(
            f"Deformable alignment: {pathlib.Path(self.moving_img).name} -> {pathlib.Path(self.fixed_img).name} | "
            f"Aligned image: moco-{pathlib.Path(self.moving_img).name} | "
            f"Initial alignment:{pathlib.Path(self.transform_files['affine']).name}"
            f" | warp file: {pathlib.Path(self.transform_files['warp']).name}")
        return self.transform_files['affine'], self.transform_files['warp'], self.transform_files['inverse_warp']

    def registration(self, registration_type: str) -> None:
        """
        Perform image registration.

        :param registration_type: The type of registration to perform ('rigid', 'affine', or 'deformable').
        :type registration_type: str
        """
        if registration_type == 'rigid':
            self.rigid()
        elif registration_type == 'affine':
            self.affine()
        elif registration_type == 'deformable':
            self.deformable()
        else:
            sys.exit("Registration type not supported!")

    def resample(self, resampled_moving_img: str, registration_type: str, segmentation="", resampled_seg="") -> None:
        """
        Resample the moving image.

        :param resampled_moving_img: The path to the resampled moving image.
        :type resampled_moving_img: str
        :param registration_type: The type of registration used to generate the transform files.
        :type registration_type: str
        :param segmentation: The path to the segmentation image (optional).
        :type segmentation: str
        :param resampled_seg: The path to the resampled segmentation image (optional).
        :type resampled_seg: str
        """
        if registration_type == 'rigid':
            cmd_to_run = self._build_cmd(resampled_moving_img, segmentation, resampled_seg,
                                         self.transform_files['rigid'])
        elif registration_type == 'affine':
            cmd_to_run = self._build_cmd(resampled_moving_img, segmentation, resampled_seg,
                                         self.transform_files['affine'])
        elif registration_type == 'deformable':
            cmd_to_run = self._build_cmd(resampled_moving_img, segmentation, resampled_seg,
                                         self.transform_files['warp'], self.transform_files['affine'])
        else:
            raise ValueError("Unknown registration type.")

        subprocess.run(cmd_to_run, shell=True, capture_output=True)

    def _build_cmd(self, resampled_moving_img: str, segmentation: str, resampled_seg: str,
                   *transform_files: str) -> str:
        """
        Build the command to resample the moving image.

        :param resampled_moving_img: The path to the resampled moving image.
        :type resampled_moving_img: str
        :param segmentation: The path to the segmentation image (optional).
        :type segmentation: str
        :param resampled_seg: The path to the resampled segmentation image (optional).
        :type resampled_seg: str
        :param transform_files: The paths to the transform files.
        :type transform_files: str
        :return: The command to resample the moving image.
        :rtype: str
        """
        cmd = f"{GREEDY_PATH} -d 3 -rf " \
              fr"{self.fixed_img} -ri LINEAR -rm " \
              fr"{self.moving_img} {resampled_moving_img}"
        if segmentation and resampled_seg:
            cmd += f" -ri LABEL 0.2vox -rm " \
                   fr"{segmentation} {resampled_seg}"
        for transform_file in transform_files:
            cmd += f" -r " \
                   fr"{transform_file}"
        return cmd


def setup_aligner(reference_image: str):
    """
    Se tup the image aligner.
    :param reference_image: The reference image.
    :type reference_image: str
    :return: The image aligner object.
    :rtype: ImageRegistration Object
    """
    return ImageRegistration(fixed_img=reference_image, multi_resolution_iterations=constants.MULTI_RESOLUTION_SCHEME)


def align_image(aligner, moving_image, output_path):
    """
    Align and resample an image.
    :param aligner: The image aligner object.
    :param moving_image: The moving image.
    :param output_path: The path to the resampled image.
    :return: None
    """
    aligner.set_moving_image(moving_image)
    aligner.registration('deformable')
    aligner.resample(resampled_moving_img=output_path, registration_type='deformable')


def find_corresponding_image(modality_dir, reference_basename):
    """
    Find the corresponding image in a modality directory.
    :param modality_dir: The modality directory.
    :param reference_basename: The basename of the reference image.
    :return: The path to the corresponding image.
    """
    pattern = reference_basename.split('_')[0] + '*.nii*'
    corresponding_images = glob.glob(os.path.join(modality_dir, pattern))
    if corresponding_images:
        return corresponding_images[0]
    else:
        logging.error(f"No corresponding image found in {modality_dir} for {reference_basename}")
        raise FileNotFoundError(f"No corresponding image found in {modality_dir} for {reference_basename}")


def align(puma_working_dir: str, ct_dir: str, pt_dir: str, mask_dir: str) -> str:
    """
    Align the images in the PUMA working directory.
    :param puma_working_dir: The path to the PUMA working directory.
    :param ct_dir: The path to the CT directory.
    :param pt_dir: The path to the PET directory.
    :param mask_dir: The path to the mask directory.
    :return: The path to the reference mask image.
    """
    reference_image = find_images(mask_dir)[0]
    logging.info(f"Reference image selected: {os.path.basename(reference_image)}")

    aligner = setup_aligner(reference_image)
    moving_images = find_images(mask_dir)
    moving_images.remove(reference_image)

    with Progress(
            "[progress.description]{task.description}",
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
            "[{task.completed}/{task.total}]",
            "[white]• Time elapsed:",  # Static text in white
            TimeElapsedColumn(),
            "[white]• CPU Load: [cyan]{task.fields[cpu]}%",  # Static label in white, dynamic content in cyan
            "[white]• Memory Load: [cyan]{task.fields[memory]}%",  # Static label in white, dynamic content in cyan
            expand=False
    ) as progress:
        task_description = "[white] Aligning images..."
        task = progress.add_task(task_description, total=len(moving_images), cpu="0", memory="0")

        for moving_image in moving_images:
            output_path = os.path.join(puma_working_dir, constants.ALIGNED_PREFIX_MASK + os.path.basename(moving_image))
            align_image(aligner, moving_image, output_path)

            # Update system loads
            cpu_load = psutil.cpu_percent(interval=None)
            memory_load = psutil.virtual_memory().percent

            progress.update(task, advance=1, refresh=True, cpu=f"{cpu_load}", memory=f"{memory_load}")
            progress.refresh()
            logging.info(f"Aligned and resampled {moving_image}")

            # Reuse the transforms for PET and CT images
            for modality_dir, modality_prefix in [(pt_dir, constants.ALIGNED_PREFIX_PT),
                                                  (ct_dir, constants.ALIGNED_PREFIX_CT)]:
                modality_image = find_corresponding_image(modality_dir, os.path.basename(moving_image))
                output_path = os.path.join(puma_working_dir, modality_prefix + os.path.basename(modality_image))
                aligner.set_moving_image(modality_image, update_transforms=False)
                aligner.resample(resampled_moving_img=output_path, registration_type='deformable')
                logging.info(f"Resampled {modality_prefix} image: {modality_image}")

    # Organizing files into their respective directories
    move_files(mask_dir, os.path.join(puma_working_dir, constants.TRANSFORMS_FOLDER), '*_affine.mat')
    move_files(mask_dir, os.path.join(puma_working_dir, constants.TRANSFORMS_FOLDER), '*warp.nii.gz')

    move_files(puma_working_dir, os.path.join(puma_working_dir, constants.ALIGNED_MASK_FOLDER),
               constants.ALIGNED_PREFIX_MASK + '*.nii*')

    for ANATOMICAL_MODALITY in ANATOMICAL_MODALITIES:
        modality_folder = f"{constants.ALIGNED_PREFIX}{ANATOMICAL_MODALITY}"
        modality_file_pattern = f"{modality_folder}_*.nii*"
        move_files(puma_working_dir, os.path.join(puma_working_dir, modality_folder), modality_file_pattern)

    for FUNCTIONAL_MODALITY in FUNCTIONAL_MODALITIES:
        modality_folder = f"{constants.ALIGNED_PREFIX}{FUNCTIONAL_MODALITY}"
        modality_file_pattern = f"{modality_folder}_*.nii*"
        move_files(puma_working_dir, os.path.join(puma_working_dir, modality_folder), modality_file_pattern)

    # get the corresponding Mask, CT and PET for the reference_image
    copy_reference_image(reference_image, os.path.join(puma_working_dir, constants.ALIGNED_MASK_FOLDER),
                         constants.ALIGNED_PREFIX_MASK)
    reference_ct = find_corresponding_image(ct_dir, os.path.basename(reference_image))
    copy_reference_image(reference_ct, os.path.join(puma_working_dir, constants.ALIGNED_CT_FOLDER),
                         constants.ALIGNED_PREFIX_CT)
    reference_pt = find_corresponding_image(pt_dir, os.path.basename(reference_image))
    copy_reference_image(reference_pt, os.path.join(puma_working_dir, constants.ALIGNED_PET_FOLDER),
                         constants.ALIGNED_PREFIX_PT)
    return reference_image


def calculate_bbox(mask_np):
    """
    Calculate the bounding box of a binary mask.

    :param mask_np: A binary mask represented as a NumPy array.
    :type mask_np: numpy.ndarray
    :return: A tuple containing the minimum and maximum coordinates of the bounding box in the format (min_coords, max_coords).
    :rtype: tuple
    :Example:
        >>> mask = np.array([[0, 0, 0, 0, 0],
        ...                  [0, 1, 1, 0, 0],
        ...                  [0, 1, 1, 0, 0],
        ...                  [0, 0, 0, 0, 0]])
        >>> calculate_bbox(mask)
        (array([1, 1]), array([2, 2]))
    """
    coords = np.array(np.where(mask_np > 0))
    return coords.min(axis=1), coords.max(axis=1)


def generate_and_apply_common_fov(mask_files: list, output_dir: str):
    """
    Generate a common field of view (FOV) mask based on the intersection of the bounding boxes of multiple binary masks,
    and apply the common FOV mask to the original masks.

    :param mask_files: A list of file paths to binary masks represented as NIfTI files.
    :type mask_files: list
    :param output_dir: The directory to save the output files.
    :type output_dir: str
    :return: None
    :rtype: None
    :Example:
        >>> mask_files = ['mask1.nii.gz', 'mask2.nii.gz', 'mask3.nii.gz']
        >>> output_dir = 'output'
        >>> generate_and_apply_common_fov(mask_files, output_dir)
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Step 1: Initialize common bounding box with the first mask
    reference_mask_file = mask_files[0]
    reference_mask = sitk.ReadImage(reference_mask_file)
    first_mask_np = sitk.GetArrayFromImage(reference_mask)
    min_coords, max_coords = calculate_bbox(first_mask_np)

    for mask_file in mask_files[1:]:
        mask = sitk.ReadImage(mask_file)
        resampled_mask_file = os.path.join(output_dir, 'RESAMPLED-' + os.path.basename(mask_file))
        resampled_mask = reslice_identity(reference_mask, mask, resampled_mask_file, True, True)
        mask_np = sitk.GetArrayFromImage(resampled_mask)
        cur_min_coords, cur_max_coords = calculate_bbox(mask_np)

        # Update the common bounding box by taking intersection
        min_coords = np.maximum(min_coords, cur_min_coords)
        max_coords = np.minimum(max_coords, cur_max_coords)

    # Create the common FOV mask based on these coordinates
    common_fov_mask_np = np.zeros_like(first_mask_np)
    common_fov_mask_np[min_coords[0]:max_coords[0] + 1,
    min_coords[1]:max_coords[1] + 1,
    min_coords[2]:max_coords[2] + 1] = 1

    common_fov_mask = sitk.GetImageFromArray(common_fov_mask_np)
    common_fov_mask.CopyInformation(reference_mask)
    common_fov_mask_file = os.path.join(output_dir, 'common_fov_mask.nii.gz')
    sitk.WriteImage(common_fov_mask, common_fov_mask_file)

    # Step 2: Apply the common FOV mask to original mask files
    for mask_file in mask_files:
        original_mask = sitk.ReadImage(mask_file)
        resampled_common_fov_file = os.path.join(output_dir, 'RESAMPLED-bb-' + os.path.basename(mask_file))
        resampled_common_fov = reslice_identity(original_mask, common_fov_mask, resampled_common_fov_file, True, True)
        original_mask_np = sitk.GetArrayFromImage(original_mask)
        resampled_common_fov_np = sitk.GetArrayFromImage(resampled_common_fov)
        modified_mask_np = original_mask_np * resampled_common_fov_np
        modified_mask = sitk.GetImageFromArray(modified_mask_np)
        modified_mask.CopyInformation(original_mask)
        sitk.WriteImage(modified_mask, mask_file)


def apply_mask(image_file, mask_file, masked_img_file):
    """
    Apply a boolean mask to an image to extract the original regions.

    Parameters:
    - image_file (str): The path to the image file.
    - mask_file (str): The path to the mask file.
    - masked_img_file (str): The path to the masked image file.

    Returns:
    - masked_img_file (str): The path to the masked image file.
    """
    image_data = nib.load(image_file).get_fdata()
    mask = nib.load(mask_file).get_fdata()
    masked_img = image_data * mask
    # save the masked image with the header of the original image
    masked_img = masked_img.astype(np.int16)
    nib.save(nib.Nifti1Image(masked_img, nib.load(image_file).affine, nib.load(image_file).header), masked_img_file)
    return masked_img_file


def normalize_data(data):
    """
    Normalize the image data to the [0, 1] range.

    :param data: The image data array.
    :type data: numpy.ndarray
    :return: The normalized image data.
    :rtype: numpy.ndarray
    """
    normalized_data = (data - np.min(data)) / (np.max(data) - np.min(data))
    return normalized_data


def get_color_channel_assignments(tracer_images) -> list:
    """
    Assign color channels to the tracer images.

    This function prompts the user to assign a color channel (Red, Green, or Blue) to each tracer image.
    The user is asked to input their choice, and the function checks if the input is valid.
    A color channel can only be assigned once. If the user's input is invalid, they are asked to input again.
    The function returns a list of color channel assignments in the order of the input tracer images.

    :param tracer_images: A list of tracer image names.
    :type tracer_images: list
    :return: A list of color channel assignments corresponding to the tracer images.
    :rtype: list
    """
    console = Console()

    color_channel_assignments = []
    channel_map = {'R': 0, 'G': 1, 'B': 2}
    line_color_map = {'R': "red", 'G': "green", 'B': "blue"}
    for tracer in tracer_images:
        valid_channels = [channel for channel in channel_map.keys() if
                          channel_map[channel] not in color_channel_assignments]
        color_channel = console.input(
            f"[white] Assign a color channel ({', '.join(valid_channels)}) for {tracer}: ").upper()
        while color_channel not in channel_map or channel_map[color_channel] in color_channel_assignments:
            sys.stdout.write('\033[F')
            sys.stdout.write('\033[K')
            color_channel = console.input(
                f"[bold_red] Invalid input. Please enter {', '.join(valid_channels)} for {tracer}: ").upper()
        color_channel_assignments.append(channel_map[color_channel])
        sys.stdout.write('\033[F')
        sys.stdout.write('\033[K')
        console.print(f"[{line_color_map[color_channel]}] Assigned color channel {color_channel} for {tracer}.")
    return color_channel_assignments


def blend_images(image_paths, modality_names, output_path, custom_colors=False):
    """
    Blend up to three NIfTI images into a single composite RGB image and create a summary table.

    Parameters:
    - image_paths (list): A list of file paths to the NIfTI images to be blended.
    - modality_names (list): A list of modality names corresponding to the images.
    - output_path (str): The path to the output file where the blended image will be saved.
    - custom_colors (bool, optional): If True, the function will prompt the user to assign a color channel to each image.
      If False, the color channels will be assigned automatically. Default is False.

    Returns:
    - None

    Raises:
    - ValueError: If the number of image paths is not between 1 and 3, or if the number of image paths and modality names do not match.
    """

    # Validate the input

    if not (1 <= len(image_paths) <= 3):
        raise ValueError(" Provide between one to three image paths.")
    if len(image_paths) != len(modality_names):
        raise ValueError(" The number of image paths and modality names must match.")

    channel_colors = ['Red', 'Green', 'Blue']
    if custom_colors:
        color_channels = get_color_channel_assignments(image_paths)
    else:
        color_channels = (0, 1, 2)

    images = []
    console = Console()
    total_steps = len(image_paths) + 2  # Loading images, blending, and saving
    with Progress() as progress:
        task = progress.add_task("[white] Processing images...", total=total_steps)

        # Load, normalize, and verify image shapes
        for path in image_paths:
            img = nib.load(path).get_fdata()
            img_normalized = normalize_data(img)
            images.append(img_normalized)
            progress.update(task, advance=1, description="[white] Loading images...")

        # Check if all images have the same shape
        if not all(img.shape == images[0].shape for img in images):
            raise ValueError(" All images must have the same dimensions.")

        progress.update(task, description="[white] Blending images...")

        # Create the composite image
        composite_data = np.zeros((*images[0].shape, 3), dtype=np.uint8)

        # Assign each image to its respective channel
        for data, color_channel in zip(images, color_channels):
            composite_data[..., color_channel] = np.clip(data * 255, 0, 255).astype(np.uint8)

        progress.update(task, advance=1)

        progress.update(task, description="[white] Saving composite image...")

        # Save the composite image as a new NIfTI file
        shape_3d = composite_data.shape[0:3]
        rgb_dtype = np.dtype([('R', 'u1'), ('G', 'u1'), ('B', 'u1')])
        composite_data = composite_data.copy().view(dtype=rgb_dtype).reshape(
            shape_3d)  # copy used to force fresh internal structure
        composite_image = nib.Nifti1Image(composite_data, nib.load(image_paths[0]).affine)
        nib.save(composite_image, output_path)

        progress.update(task, advance=1)
        progress.stop()  # Manually stop the progress display

    table = Table(show_header=True, header_style="bold magenta", border_style="white")

    # Add columns with specific style adjustments
    table.add_column("Index", style="dim white", justify="center")
    table.add_column("Generated File Names", style="white", overflow="fold", justify="center")
    table.add_column("Modality Type", style="white", justify="center")
    table.add_column("Channel Assigned", style="white", justify="center")

    # Add rows with your data
    for idx, (path, modality, color_channel) in enumerate(zip(image_paths, modality_names, color_channels)):
        table.add_row(str(idx + 1), path, modality, channel_colors[color_channel])

    # Adding the composite image details to the table
    composite_index = len(image_paths) + 1
    table.add_row(str(composite_index), output_path, "MPX", "RGB")

    # Print the table
    console.print(table)

    # Renaming according to channel assignments
    for image_path, color_channel in zip(image_paths, color_channels):
        directory = os.path.dirname(image_path)
        filename = os.path.basename(image_path)
        channel_prefix = constants.CHANNEL_PREFIXES[color_channel]

        if filename.endswith('.nii.gz'):
            base_name = filename.rsplit('.nii.gz')[0]
            extension = '.nii.gz'
        elif filename.endswith('.nii'):
            base_name = filename.rsplit('.nii')[0]
            extension = '.nii'
        else:
            return

        new_image_path = os.path.join(directory, f"{base_name}{channel_prefix}{extension}")
        os.rename(image_path, new_image_path)


def multiplex(directory, extension, modality, output_image_path, custom_colors=False):
    """
    Multiplex the images in a directory into a single composite RGB image.
    :param custom_colors: Specifies if user defined RGB channel assignment should be used.
    :param directory: The directory containing the images.
    :type directory: str
    :param extension: The extension of the images.
    :type extension: str
    :param modality: The modality of the images.
    :type modality: str
    :param output_image_path: The path to the output image.
    :type output_image_path: str
    :return: None
    """
    nifti_files = get_files(directory, extension)
    modalities = [modality] * len(nifti_files)
    blend_images(nifti_files, modalities, output_image_path, custom_colors)


def rgb2gray(rgb_file: str, gray_file: str):
    """
    Convert a 3D RGB image to grayscale.
    This function converts a 3D RGB image to grayscale using the formula:
    Y = 0.299 * R + 0.587 * G + 0.114 * B. The resulting grayscale image is saved as a new NIfTI file.
    :param rgb_file: The path to the RGB image.
    :type rgb_file: str
    :param gray_file: The path to the grayscale image.
    :type gray_file: str
    :return: None
    """
    c3d_cmd = f"{C3D_PATH} -mcs {rgb_file} -wsum {RED_WEIGHT} {GREEN_WEIGHT} {BLUE_WEIGHT} -o {gray_file}"
    subprocess.run(c3d_cmd, shell=True, capture_output=True)
    logging.info(f" Converted {os.path.basename(rgb_file)} to grayscale.")


# use lionz to segment the tumors from the grayscale image

def segment_tumors(input_dir: str, output_dir: str):
    """
    Segment tumors from a grayscale image using the LIONz model.
    :param input_dir: The path to the input directory.
    :type input_dir: str
    :param output_dir: The directory to save the output files.
    :type output_dir: str
    :return: None
    """
    device = check_device()
    logging.info(f" Running LIONz for segmenting tumors from {input_dir}")
    lion(LIONZ_MODEL, input_dir, output_dir, device)
    logging.info(f" Tumor segmentation completed.")
