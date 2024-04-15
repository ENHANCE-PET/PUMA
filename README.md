![Puma-logo](Images/Puma-logo.png)

## PUMA 1.0 🐾 -  One Image multiple perspectives 🎭
[![PyPI version](https://img.shields.io/pypi/v/pumaz?color=FF1493&style=flat-square&logo=pypi)](https://pypi.org/project/pumaz/) [![License: GPL v3](https://img.shields.io/badge/License-GPLv3-red.svg?style=flat-square&logo=gnu&color=FF0000)](https://www.gnu.org/licenses/gpl-3.0) [![Monthly Downloads](https://img.shields.io/pypi/dm/pumaz?label=Downloads%20(Monthly)&color=9400D3&style=flat-square&logo=python)](https://pypi.org/project/pumaz/) [![Daily Downloads](https://img.shields.io/pypi/dd/pumaz?label=Downloads%20(Daily)&color=9400D3&style=flat-square&logo=python)](https://pypi.org/project/pumaz/) <!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
[![All Contributors](https://img.shields.io/badge/all_contributors-1-orange.svg?style=flat-square)](#contributors-)
<!-- ALL-CONTRIBUTORS-BADGE:END -->

Get ready for a leap in the world of Positron Emission Tomography (PET) imaging: introducing PUMA 1.0 🚀

PUMA 1.0 (PET Universal Multi-tracer Aligner) has been crafted with a strong focus on the challenges of clinical PET imaging.

⚡ It's Agile: PUMA operates across all operating systems and architectures, from x86 to ARM64 (Apple Silicon). It has no specific hardware needs, and with the requirement for Python 3.9 or above, PUMA 1.0 is ready to perform anywhere, anytime.

🔍 It's Precision-Driven yet blazingly fast: Built upon the bedrock of nnUNet based MOOSE and advanced diffeomorphic registration techniques from the awesome 'greedy' library, PUMA 1.0 aligns multiplexed tracer images with high precision in less than a heartbeat, clocking in at under one minute, offering unrivaled clarity and accuracy in the diagnosis of patient pathology.

🗝️ It's Empowering: PUMA 1.0 enhances diagnostic capabilities with its multiplexed viewing angles, unlocking a new realm of diagnostic possibilities and empowering clinicians.

Join us on this revolutionary journey with PUMA 1.0.

## 🚀 PUMA's multiplexing in action

<div align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://github.com/Keyn34/PUMA/blob/master/Images/PUMA-Flex.gif">
  <source media="(prefers-color-scheme: light)" srcset="https://github.com/Keyn34/PUMA/blob/master/Images/PUMA-Flex.gif">
  <img alt="Shows an illustrated MOOSE story board adopted to different themes" src="https://github.com/Keyn34/PUMA/blob/master/Images/PUMA-Flex.gif">
</picture>
</div>

## Requirements ✅

Before stepping into the future with PUMA 1.0, here's what you need for an optimal experience:

- **Operating System**: Windows, Mac, or Linux - PUMA 1.0 is versatile and works across all these platforms.

- **Memory**: Make sure your system has enough memory (8-16 GB) to run the tasks smoothly.

- **GPU**: You need a cuda enabled GPU (NVIDIA), 8 GB or more!

- **Python**: PUMA 1.0 operates with Python 3.10, staying in line with the latest updates.

Once these specifications are met, you're all set to experience PUMA 1.0's capabilities.

## Installation Guide 🛠️

Installation is a breeze on Windows, Linux, and MacOS. Follow the steps below to start your journey with PUMA 1.0.

### For Linux and MacOS 🐧🍏

1. Create a Python environment named 'puma-env' or as per your preference.
   ```bash
   python3 -m venv puma-env
   ```

2. Activate the environment.
   ```bash
   source puma-env/bin/activate  # for Linux
   source puma-env/bin/activate  # for MacOS
   ```

3. Install PUMA 1.0.
   ```bash
   pip install pumaz
   ```

Congratulations! You're all set to start using PUMA 1.0.

### For Windows 🪟

1. Create a Python environment, e.g., 'puma-env'.
   ```bash
   python -m venv puma-env
   ```

2. Activate the environment.
   ```bash
   .\puma-env\Scripts\activate
   ```

3. Install PUMA 1.0.
   ```bash
   pip install pumaz
   ```

You're now ready to experience the precision and speed of PUMA 1.0.

## Usage Guide 📚

Start your journey with PUMA 1.0 by using our straightforward command-line tool. It requires the directory path containing different tracer images, and each image should be stored in separate folders. Here's how you can get started:

```bash

   pumaz \
       -d <path_to_image_dir>              # Directory path containing the images to be analyzed
       -ir <regions_to_ignore>             # Regions to ignore: arms, legs, head, none
       -m                                  # Optional: Enable multiplexed RGB image output
       -cs <color_selection>               # Optional: Custom color selection for RGB output (requires -m)
       -c2d <convert_back_to_dicom>        # Optional: Once set, the generated nifti images will be converted back to DICOM
```

- `<path_to_image_dir>` refers to the parent directory containing different tracer images in their respective sub-directories.

- `-ir` specifies the regions to be ignored during registration. If you don't want to ignore any regions, use `none`. If you want to ignore the arms, legs, or head during registration, pass the corresponding regions delimited by a `,`. For example: `-ir head,arms` to ignore the head and arms.

- `-m` will activate the output of a multiplexed RGB image of the combined tracer images.

- `-cs`, when passed along with `-m`, PUMA will ask you to provide a custom order of color channels for the corresponding tracer images. That way, you can freely decide which tracer image is associated with which channel.
- `-c2d`, when set the generated aligned nifti images will be converted back to DICOM.
  
For assistance or additional information, you can always type:

```bash
pumaz -h
```

### Example usage:
Apply PUMA to images in a directory, ignoring arms and legs, with multiplexed RGB output and custom colors:

```bash
    pumaz -d /path/to/images -ir arms,legs -m -cs -c2d 
```

## Directory Structure and Naming Conventions for PUMA 📂🏷️

PUMA 1.0 requires your data to be structured in a certain way. It supports DICOM directories and NIFTI files. For NIFTI files, users need to ensure that the files are named with the correct modality tag at the start.

### Required Directory Structure 🌳

Here is the directory structure that PUMA 1.0 expects:

```
Parent_Directory
│
└───Tracer1 # can be named anything
│   │
│   └───PET_DICOM_Directory or PT_xxxx.nii.gz # If it's DICOM, the folder name can be anything, but if nifti use a prefix 'PT' for PET
│   │
│   └───CT_DICOM_Directory or CT_xxxx.nii.gz # If it's DICOM, the folder name can be anything, but if nifti use a prefix 'CT' for CT
│
└───Tracer2
│   │
│   └───PET_DICOM_Directory or PT_xxxx.nii.gz
│   │
│   └───CT_DICOM_Directory or CT_xxxx.nii.gz
...

└───Tracer3
    │
    └───PET_DICOM_Directory or PT_xxxx.nii.gz
    │
    └───CT_DICOM_Directory or CT_xxxx.nii.gz
```

### Naming Conventions 🏷️

- For DICOM directories, no specific naming is required.
- For NIFTI files, the file should start with the DICOM modality tag (e.g., 'PT_' or 'CT_') followed by the desired name. For example, 'PT_MySample.nii.gz'.

Note: All the PET and CT images related to a tracer should be placed in the same directory named after the tracer.

## 🚀 Benchmarks

- [Apple Intel 4 Cores | Device: CPU | Archictecture: x86_64 | ~25 min](https://github.com/Keyn34/PUMA/blob/master/Images/Apple-intel-4-core.png)
- [Apple M1 Ultra 20 Cores | Device: CPU | Archictecture: ARM | ~12 min](https://github.com/Keyn34/PUMA/blob/master/Images/Apple-M1-Ultra-20-Cores.png)
- [Linux Server 128 Cores | Nvidia A100 GPU | Architecture: x86_64 | ~10 min](https://github.com/Keyn34/PUMA/blob/master/Images/Linux-Server-Nvidia-A100-128-Cores.png)

## A Note on QIMP Python Packages: The 'Z' Factor 📚🚀

All of our Python packages here at QIMP carry a special signature – a distinctive 'Z' at the end of their names. The 'Z' is more than just a letter to us; it's a symbol of our forward-thinking approach and commitment to continuous innovation.

Our PUMA package, for example, is named as 'pumaz', pronounced "puma-see". So, why 'Z'?

Well, in the world of mathematics and science, 'Z' often represents the unknown, the variable that's yet to be discovered, or the final destination in a series. We at QIMP believe in always pushing boundaries, venturing into uncharted territories, and staying on the cutting edge of technology. The 'Z' embodies this philosophy. It represents our constant quest to uncover what lies beyond the known, to explore the undiscovered, and to bring you the future of medical imaging.

Each time you see a 'Z' in one of our package names, be reminded of the spirit of exploration and discovery that drives our work. With QIMP, you're not just installing a package; you're joining us on a journey to the frontiers of medical image processing. Here's to exploring the 'Z' dimension together! 🚀
 

## Contributors ✨

Thanks goes to these wonderful people ([emoji key](https://allcontributors.org/docs/en/emoji-key)):

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tbody>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/W7ebere"><img src="https://avatars.githubusercontent.com/u/166598214?v=4?s=100" width="100px;" alt="W7ebere"/><br /><sub><b>W7ebere</b></sub></a><br /><a href="https://github.com/LalithShiyam/PUMA/commits?author=W7ebere" title="Documentation">📖</a></td>
    </tr>
  </tbody>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification. Contributions of any kind welcome!
