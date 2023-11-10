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
from moosez import moose
from mpire import WorkerPool
from rich.progress import Progress, BarColumn, TimeElapsedColumn

from pumaz import constants
from pumaz import file_utilities
from pumaz.constants import GREEDY_PATH
from pumaz.file_utilities import create_directory, move_file, remove_directory, move_files_to_directory, get_files


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
            "• Time elapsed:",
            TimeElapsedColumn(),
            "• CPU Load: [cyan]{task.fields[cpu]}%",
            "• Memory Load: [cyan]{task.fields[memory]}%",
            "• GPU Load: [cyan]{task.fields[gpu]}%",
            expand=False
    ) as progress:
        task_description = f"[cyan] MOOSE-ing CT files | Model: {moose_model} | Accelerator: {accelerator}"
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
        ct_file = glob.glob(os.path.join(subdir, 'CT*.nii*'))
        pt_file = glob.glob(os.path.join(subdir, 'PET*.nii*'))
        resliced_ct_file = os.path.join(subdir, constants.RESAMPLED_PREFIX + str(i) + '_' +
                                        os.path.basename(subdir) + '_' +
                                        os.path.basename(ct_file[0]))

        tasks.append((
            sitk.ReadImage(pt_file[0]),
            sitk.ReadImage(ct_file[0]),
            resliced_ct_file,
            False,
            False
        ))
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
    body_mask_dir = os.path.join(puma_working_dir, constants.BODY_MASK_FOLDER)
    puma_mask_dir = os.path.join(puma_working_dir, constants.PUMA_MASK_FOLDER)
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

    process_and_moose_ct_files(ct_dir, body_mask_dir, constants.MOOSE_MODEL_BODY, constants.ACCELERATOR)
    process_and_moose_ct_files(ct_dir, puma_mask_dir, constants.MOOSE_MODEL_PUMA, constants.ACCELERATOR)

    # Generate mask with common field of view

    body_mask_files = glob.glob(os.path.join(body_mask_dir, constants.MOOSE_PREFIX_BODY + '*nii*'))
    # generate_and_apply_common_fov(body_mask_files, os.path.join(puma_working_dir, constants.COMMON_FOV_MASK_FOLDER))

    for mask_file in body_mask_files:
        new_mask_file = re.sub(rf'{constants.MOOSE_PREFIX_BODY}', '', mask_file)
        os.rename(mask_file, new_mask_file)
        change_mask_labels(new_mask_file, constants.MOOSE_LABEL_INDEX, regions_to_ignore)

    # remove arms from the puma masks

    puma_mask_files = glob.glob(os.path.join(puma_mask_dir, constants.MOOSE_PREFIX_PUMA + '*nii*'))
    for puma_mask_file in puma_mask_files:
        new_mask_file = re.sub(rf'{constants.MOOSE_PREFIX_PUMA}', '', puma_mask_file)
        os.rename(puma_mask_file, new_mask_file)
        apply_mask(new_mask_file, os.path.join(body_mask_dir, os.path.basename(new_mask_file)), new_mask_file)

    return puma_working_dir, ct_dir, pt_dir, puma_mask_dir


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

        cmd_to_run = f"{GREEDY_PATH} -d 3 -a -i " \
                     fr"{self.fixed_img} {self.moving_img} " \
                     f"{combined_mask_cmd} -ia-image-centers -dof 6 -o " \
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

        cmd_to_run = f"{GREEDY_PATH} -d 3 -a -i " \
                     fr"{self.fixed_img} {self.moving_img} " \
                     f"{combined_mask_cmd} -ia-image-centers -dof 12 -o " \
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


def setup_aligner(reference_image: str):
    """
    Setup the image aligner.
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


def move_files(source_dir, destination_dir, pattern):
    """
    Move files from a source directory to a destination directory based on a pattern.
    :param source_dir: The source directory.
    :param destination_dir: The destination directory.
    :param pattern: The pattern to search for.
    :return: None
    """
    file_utilities.create_directory(destination_dir)
    for file_path in find_images(source_dir, pattern):
        file_utilities.move_file(file_path, destination_dir)
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
    file_utilities.copy_file(source_image, destination_path)
    logging.info(f"Copied {source_image} to {destination_path}")


def align(puma_working_dir: str, ct_dir: str, pt_dir: str, mask_dir: str):
    """
    Align the images in the PUMA working directory.
    :param puma_working_dir: The path to the PUMA working directory.
    :param ct_dir: The path to the CT directory.
    :param pt_dir: The path to the PET directory.
    :param mask_dir: The path to the mask directory.
    :return: None
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
            "• Time elapsed:",
            TimeElapsedColumn(),
            "• CPU Load: [cyan]{task.fields[cpu]}%",
            "• Memory Load: [cyan]{task.fields[memory]}%",
            expand=False
    ) as progress:
        task_description = "[cyan] Aligning images..."
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
    copy_reference_image(reference_image, os.path.join(puma_working_dir, constants.ALIGNED_MASK_FOLDER),
                         constants.ALIGNED_PREFIX)
    move_files(puma_working_dir, os.path.join(puma_working_dir, constants.ALIGNED_CT_FOLDER),
               constants.ALIGNED_PREFIX_CT + '*.nii*')
    move_files(puma_working_dir, os.path.join(puma_working_dir, constants.ALIGNED_PET_FOLDER),
               constants.ALIGNED_PREFIX_PT + '*.nii*')


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
    nib.save(nib.Nifti1Image(masked_img, nib.load(image_file).affine, nib.load(image_file).header), masked_img_file)
    return masked_img_file
