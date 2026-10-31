# Runtime compatibility tests

Run with PUMA's real image-conversion dependencies installed:

```sh
python -m pytest tests/functional -q
```

The DICOM conversion regression creates a small synthetic CT series at runtime,
passes it through PUMA's normal directory-standardization helper, and verifies
scaled voxel values and independently calculated physical coordinates. It needs
NumPy, nibabel, pydicom, dicom2nifti, SimpleITK and nifti2dicom, in addition to the
lightweight security-test dependencies. No model inference or clinical data is
used. The lightweight CI workflow intentionally runs `tests/test_security.py`;
run bare `python -m pytest -q` in a runtime environment to run both suites.
