![Puma-logo](Images/Puma-logo.png)

## PUMA 1.0 🐾 - Agile. Precision-Driven. Empowering 💪

Get ready for a leap in the world of Positron Emission Tomography (PET) imaging: introducing PUMA 1.0 🚀

PUMA 1.0 (PET Universal Multi-tracer Aligner) has been crafted with a strong focus on the challenges of clinical PET imaging.

⚡ It's Agile: PUMA operates across all operating systems and architectures, from x86 to ARM64 (Apple Silicon). It has no specific hardware needs, and with the requirement for Python 3.9 or above, PUMA 1.0 is ready to perform anywhere, anytime.

🔍 It's Precision-Driven yet blazingly fast: Built upon the bedrock of advanced diffeomorphic registration techniques from the awesome 'greedy' library, PUMA 1.0 aligns multiplexed tracer images with high precision in less than a heartbeat, clocking in at under one minute, offering unrivaled clarity and accuracy in the diagnosis of patient pathology.

🗝️ It's Empowering: PUMA 1.0 enhances diagnostic capabilities with its multiplexed viewing angles, unlocking a new realm of diagnostic possibilities and empowering clinicians.

Join us on this revolutionary journey with PUMA 1.0.

## Requirements ✅

Before stepping into the future with PUMA 1.0, here's what you need for an optimal experience:

- **Operating System**: Windows, Mac, or Linux - PUMA 1.0 is versatile and works across all these platforms.

- **Memory**: Make sure your system has enough memory (8-16 GB) to run the tasks smoothly.

- **GPU**: You need a cuda enabled GPU (NVIDIA), 8 GB or more!

- **Python**: PUMA 1.0 operates with Python 3.9 or above, staying in line with the latest updates.

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
pumaz -d <path_to_image_dir>
```

Here `<path_to_image_dir>` refers to the parent directory containing different tracer images in their respective sub-directories.

For assistance or additional information, you can always type:

```bash
pumaz -h
```

## Directory Structure and Naming Conventions for PUMA 📂🏷️

PUMA 1.0 requires your data to be structured in a certain way. It supports DICOM directories and NIFTI files. For NIFTI files, users need to ensure that the files are named with the correct modality tag at the start.

### Required Directory Structure 🌳

Here is the directory structure that PUMA 1.0 expects:

```
Parent_Directory
│
└───Tracer1
│   │
│   └───PET_DICOM_Directory or PET_xxxx.nii.gz
│   │
│   └───CT_DICOM_Directory or CT_xxxx.nii.gz
│
└───Tracer2
│   │
│   └───PET_DICOM_Directory or PET_xxxx.nii.gz
│   │
│   └───CT_DICOM_Directory or CT_xxxx.nii.gz
...

└───Tracer3
    │
    └───PET_DICOM_Directory or PET_xxxx.nii.gz
    │
    └───CT_DICOM_Directory or CT_xxxx.nii.gz
```

### Naming Conventions 🏷️

- For DICOM directories, no specific naming is required.
- For NIFTI files, the file should start with the modality tag (e.g., 'PET_' or 'CT_') followed by the desired name. For example, 'PET_MySample.nii.gz'.

Note: All the PET and CT images related to a tracer should be placed in the same directory named after the tracer.

## To do  🚧

**PUMA v.1.0: August 2023 release candidate**

- [x] Train moose to remove the CT bed and patient arms, to improve registration accuracy [@mprires](https://github.com/mprires)
- [x] Implement the generated model to puma as a preprocessing step before initiating the alignment [@LalithShiyam](https://github.com/LalithShiyam)

## A Note on QIMP Python Packages: The 'Z' Factor 📚🚀

All of our Python packages here at QIMP carry a special signature – a distinctive 'Z' at the end of their names. The 'Z' is more than just a letter to us; it's a symbol of our forward-thinking approach and commitment to continuous innovation.

Our PUMA package, for example, is named as 'pumaz', pronounced "puma-see". So, why 'Z'?

Well, in the world of mathematics and science, 'Z' often represents the unknown, the variable that's yet to be discovered, or the final destination in a series. We at QIMP believe in always pushing boundaries, venturing into uncharted territories, and staying on the cutting edge of technology. The 'Z' embodies this philosophy. It represents our constant quest to uncover what lies beyond the known, to explore the undiscovered, and to bring you the future of medical imaging.

Each time you see a 'Z' in one of our package names, be reminded of the spirit of exploration and discovery that drives our work. With QIMP, you're not just installing a package; you're joining us on a journey to the frontiers of medical image processing. Here's to exploring the 'Z' dimension together! 🚀
 
