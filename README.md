![Puma-logo](Images/Puma-logo.png)

## PUMA 1.0 — Multiplexed PET, Ready for Practice
[![PyPI version](https://img.shields.io/pypi/v/pumaz?color=0b7285&style=flat-square&logo=pypi)](https://pypi.org/project/pumaz/) [![License: GPL v3](https://img.shields.io/badge/License-GPLv3-555555.svg?style=flat-square&logo=gnu)](https://www.gnu.org/licenses/gpl-3.0) [![Monthly Downloads](https://img.shields.io/pypi/dm/pumaz?label=Monthly%20Downloads&color=6a4c93&style=flat-square&logo=python)](https://pypi.org/project/pumaz/)

---

**PUMA turns serial PET/CT acquisitions into a single, context-rich view.** The pipeline multiplexes tracer studies, aligns anatomy, and produces consistent reporting assets so clinicians and researchers can read more in less time. 

### Why teams choose PUMA 🧠
- **Multiplexed insight** – Fuse several tracer volumes into colour-encoded composites without sacrificing quantitative context.
- **Trusted accuracy** – nnU-Net driven segmentations and diffeomorphic registration keep tumour boundaries and uptake values reliable.
- **Workflow friendly** – One CLI coordinates preprocessing, registration, blending, and export, keeping radiologists and physicists in sync.
- **Platform agnostic** – Linux, Windows, and macOS (including Apple Silicon) run the same wheel; PyTorch’s upstream MPS backend covers 3D convolutions with no custom build.

### Quick start 🚀
1. Install the package: `pip install pumaz`
2. Arrange tracer folders as described in 🔗 [Workflow essentials](#workflow-essentials).
3. Launch a run:

<div align="center">

```bash
pumaz -d /path/to/patient -m -ir arms,legs,head
```

</div>

PUMA aligns each tracer, multiplexes RGB composites when requested, and writes results to a timestamped `PUMAZ-v<version>-YYYY-MM-DD-HH-MM-SS` folder beside your subject data. A run log (`pumaz-v.<clock>.log`) is saved in the working directory.

### Installation 🛠️
- **Using uv (recommended)**  
  ```bash
  curl -Ls https://astral.sh/uv/install.sh | sh  # install uv if needed
  uv venv .venv
  source .venv/bin/activate
  uv pip install pumaz
  ```
  To add PUMA to an existing `uv` project, run `uv add pumaz`.
- **Using pip**  
  ```bash
  pip install pumaz
  ```
- **From source (development work)**  
  ```bash
  git clone https://github.com/ENHANCE-PET/PUMA.git
  cd PUMA
  uv pip install -e .
  ```
  Use Python 3.10+ and create a virtual environment when possible.

### Usage essentials 🧾
Retrieve the full command reference with:
```bash
pumaz --help
```

Common flags:
- `-d /path/to/patient` – Root directory that contains one subfolder per tracer.
- `-ir arms,legs` – Skip specified body regions during registration (`none` by default).
- `-m` – Produce multiplexed RGB composites alongside individual tracer outputs.
- `-cm Tracer1:R,...` – Assign explicit colour channels to each tracer (mutually exclusive with `-cs`).
- `-cs` – Interactively choose channel assignments when `-m` is enabled.
- `-c2d` – Convert aligned NIfTI volumes back to DICOM.

### <a id="workflow-essentials"></a>Workflow essentials 🧬
Organise every patient or study with one directory per tracer; each tracer must contain PET and CT data as DICOM folders or NIfTI files prefixed by modality:

```
Parent_Directory/
├── Tracer1/
│   ├── PT_series.nii.gz    # or PET DICOM directory
│   └── CT_series.nii.gz    # or CT DICOM directory
├── Tracer2/
│   ├── PT_series.nii.gz
│   └── CT_series.nii.gz
└── Tracer3/
    ├── PT_series.nii.gz
    └── CT_series.nii.gz
```

Ensure PET/CT pairs are spatially corresponding within each tracer directory for best results.

### Output artefacts 📁
Each run emits a timestamped workspace (`PUMAZ-v<version>-<timestamp>`) alongside your tracer folders:

| Path | Contents |
|------|----------|
| `CT/` | Resliced CT volumes staged for registration |
| `PT/` | Resliced PET volumes indexed by tracer order |
| `aligned_CT/` | Final aligned CT volumes |
| `aligned_MASK/` | Aligned segmentation masks |
| `aligned_PT/` | Aligned PET volumes; includes `RGB-composite.nii.gz` and `grayscale-composite.nii.gz` when multiplexing |
| `body_masks/` | Body-region masks with ignored labels removed |
| `puma_masks/` | 24-label PUMA segmentations |
| `transforms/` | Affine and warp fields for every tracer |

- Logs live alongside the run (`pumaz-v.<clock>.log`); batch failures append to `pumaz-failures-YYYYMMDD-HHMMSS.log`.
- Passing `--convert-to-dicom` creates `_dicom` folders inside `aligned_PT/` with `Processed-by-PUMA` metadata.

### Platform support 💻
PUMA runs on CPU or GPU across major operating systems. PyTorch ≥2.1 ships native Metal (MPS) support, so Apple Silicon users can install the standard wheel—no custom forks or 3D-convolution patches required.

### Benchmarks 📊
Performance benchmarks and reference datasets are in preparation. If you want early numbers or to contribute your own results, open an issue.

### Support and roadmap 🤝
- File bugs or feature requests on the 🔗 [issue tracker](https://github.com/ENHANCE-PET/PUMA/issues).
- Commercial support and integration services are available via 🔗 [Zenta Solutions](mailto:lalith.shiyam@zenta.solutions).
- The near-term roadmap includes automated QA scoring, longitudinal dashboards, and cloud-friendly batching.

### Citation 📚
If you use PUMA in your research, please cite:

> **L.K. Shiyam Sundar, S. Gutschmayer, M. Pires, _et al._**  
> “Fully Automated Image-Based Multiplexing of Serial PET/CT Imaging for Facilitating Comprehensive Disease Phenotyping.”  
> _Journal of Nuclear Medicine_, September 2025. doi:[10.2967/jnumed.125.269688](https://doi.org/10.2967/jnumed.125.269688)

### The QIMP “Z” signature ✨
Every QIMP library carries a trailing “z” to signal curiosity for what comes next. It nods to the unknown variable in science and to our commitment to keep stretching medical imaging beyond the expected. When you install `pumaz`, you join that exploration.

### License ⚖️
The open-source edition ships under GPLv3. For commercial licensing or OEM partnerships, contact [lalith.shiyam@zenta.solutions](mailto:lalith.shiyam@zenta.solutions).

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0) [![Commercial License](https://img.shields.io/badge/Commercial--Use-Contact--Zenta-orange)](mailto:lalith.shiyam@zenta.solutions)

### Contributors 🙌

Thanks to every contributor—large and small—for shaping PUMA.

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tbody>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/W7ebere"><img src="https://avatars.githubusercontent.com/u/166598214?v=4?s=100" width="100px;" alt="W7ebere"/><br /><sub><b>W7ebere</b></sub></a><br /><a href="https://github.com/ENHANCE-PET/PUMA/commits?author=W7ebere" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/mprires"><img src="https://avatars.githubusercontent.com/u/48754309?v=4?s=100" width="100px;" alt="Manuel Pires"/><br /><sub><b>Manuel Pires</b></sub></a><br /><a href="https://github.com/ENHANCE-PET/PUMA/commits?author=mprires" title="Code">💻</a> <a href="https://github.com/ENHANCE-PET/PUMA/commits?author=mprires" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/Keyn34"><img src="https://avatars.githubusercontent.com/u/87951050?v=4?s=100" width="100px;" alt="Sebastian Gutschmayer"/><br /><sub><b>Sebastian Gutschmayer</b></sub></a><br /><a href="https://github.com/ENHANCE-PET/PUMA/commits?author=Keyn34" title="Code">💻</a> <a href="https://github.com/ENHANCE-PET/PUMA/commits?author=Keyn34" title="Documentation">📖</a></td>
    </tr>
  </tbody>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification. Contributions of any kind are welcome.
