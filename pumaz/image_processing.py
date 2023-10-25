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


def process_and_moose_ct_files(ct_dir: str, mask_dir: str, moose_model: str, accelerator: str) -> None:
    """
    Process CT files using MOOSE.

    :param ct_dir: The directory containing the CT files.
    :type ct_dir: str
    :param mask_dir: The directory to save the MOOSE masks.
    :type mask_dir: str
    :param moose_model: The path to the MOOSE model.
    :type moose_model: str
    :param accelerator: The accelerator to use for MOOSE.
    :type accelerator: str
    :return: None
    :rtype: None
    :Example:
        >>> process_and_moose_ct_files('/path/to/ct_dir', '/path/to/mask_dir', '/path/to/moose_model', 'cpu')
    """
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
        ('/path/to/puma_working_dir', '/path/to/ct_dir', '/path/to/pt_dir', '/path/to/mask_dir')
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

    # Generate mask with common field of view

    mask_files = glob.glob(os.path.join(mask_dir, constants.MOOSE_PREFIX + '*nii*'))
    generate_and_apply_common_fov(mask_files, os.path.join(puma_working_dir, constants.COMMON_FOV_MASK_FOLDER))

    for mask_file in glob.glob(os.path.join(mask_dir, constants.MOOSE_PREFIX + '*')):
        new_mask_file = re.sub(rf'{constants.MOOSE_PREFIX}', '', mask_file)
        os.rename(mask_file, new_mask_file)
        change_mask_labels(new_mask_file, constants.MOOSE_LABEL_INDEX, regions_to_ignore)

    return puma_working_dir, ct_dir, pt_dir, mask_dir


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

    def __init__(self, fixed_img: str, multi_resolution_iterations: str, fixed_mask: str = None):
        self.fixed_img = fixed_img
        self.fixed_mask = fixed_mask
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
        """
        Perform affine alignment.

        :return: The path to the affine transform file.
        :rtype: str
        """
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
        """
        Perform deformable alignment.

        :return: A tuple containing the paths to the rigid, warp, and inverse warp transform files.
        :rtype: tuple
        """
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
                                         self.transform_files['warp'], self.transform_files['rigid'])
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
        cmd = f"{GREEDY_PATH} -d 3 -rf {re.escape(self.fixed_img)} -ri LINEAR -rm " \
              f"{re.escape(self.moving_img)} {re.escape(resampled_moving_img)}"
        if segmentation and resampled_seg:
            cmd += f" -ri LABEL 0.2vox -rm {re.escape(segmentation)} {re.escape(resampled_seg)}"
        for transform_file in transform_files:
            cmd += f" -r {re.escape(transform_file)}"
        return cmd


def align(puma_working_dir: str, ct_dir: str, pt_dir: str, mask_dir: str):
    """
    Align CT and PET images to a common frame using deformable registration.

    :param puma_working_dir: The working directory for PUMA.
    :type puma_working_dir: str
    :param ct_dir: The directory containing the CT images.
    :type ct_dir: str
    :param pt_dir: The directory containing the PET images.
    :type pt_dir: str
    :param mask_dir: The directory containing the binary masks.
    :type mask_dir: str
    :return: None
    :rtype: None
    :Example:
        >>> puma_working_dir = '/path/to/puma/working/dir'
        >>> ct_dir = '/path/to/ct/dir'
        >>> pt_dir = '/path/to/pt/dir'
        >>> mask_dir = '/path/to/mask/dir'
        >>> align(puma_working_dir, ct_dir, pt_dir, mask_dir)
    """
    ct_files = sorted(glob.glob(os.path.join(ct_dir, '*.nii*')))
    reference_image = ct_files[0]
    logging.info(f"Reference image: {pathlib.Path(reference_image).name}")
    fixed_mask = glob.glob(os.path.join(mask_dir, os.path.basename(reference_image).split('_')[0] + '*.nii*'))[0]
    moving_images = [ct_file for ct_file in ct_files if ct_file != reference_image]

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
