# Security audit — 2026-10-31

Scope: source, executable downloads/cache upgrades, release workflow, and declared
runtime dependencies. Tests use synthetic filenames/archives; no imaging data or
model weights were downloaded or added.

## Repairs

- Replaced all Greedy/c3d shell command strings with argument lists and checked
  subprocess results. Filenames containing spaces or shell punctuation cannot
  execute shell commands.
- Passed release tags through an environment variable before validation, closing
  command substitution through direct GitHub-expression interpolation in Bash.
- Pinned the five v1.8.10 binary ZIP SHA-256 digests from GitHub release asset
  metadata. Bound compressed downloads to 256 MiB and extracted content to 1 GiB
  / 10,000 members; reject traversal, unexpected roots and special/link members.
- Download/extract privately; refresh legacy caches lacking the matching digest
  marker even when old executables are present. Publish fresh files only after
  validation, restore the old bundle on publication failure, and retain a
  recoverable backup if restoration also fails. Fresh files replace prior Windows
  Everyone:F grants; permission setup no longer grants Everyone full control.
- Raised pydicom to >=3.0.2 and Pillow to >=13. Require Python >=3.11 to support
  the patched Pillow line. Added known vulnerable transitive dependency floors
  for torch, anyio, certifi, filelock, fsspec, msgpack, setuptools and urllib3.
  requirements.txt delegates to project metadata, removing its obsolete Moose pin.

## Verification

- 14 security regressions pass, with observed failures before the corresponding
  fixes. Tests execute synthetic native tools and workflow Bash, exercise
  integrity/path checks, legacy cache refresh and single/double rollback failures.
- Parent independent PUMA source review: GO; independently reran 13 tests.
- Fresh Python 3.11 dependency resolution succeeds with the final constraints.
- Final Python 3.11 resolved graph: pip-audit checked 112 packages, none skipped,
  and reported no known vulnerabilities. Source distribution and wheel builds pass.
- `git diff --check` passes. No model inference or real registration was executed.

## Evidence and limits

- pydicom advisory: https://github.com/advisories/GHSA-v856-2rf8-9f28
- Binary digest source:
  https://api.github.com/repos/ENHANCE-PET/PUMA/releases/tags/pumaz-v.1.8.10
- Dependency floors also reconcile current GitHub advisory evidence shared by the
  coordinated repository audit. A clean advisory scan is not proof of no defects.
- Native binaries are trusted upstream releases, not audited machine code.
  Windows ACL migration was tested through the portable replacement behavior;
  native Windows execution/ACL evaluation and real registration were not run.
- Verified cache markers attest installation provenance, not protection against
  subsequent changes by an account already able to modify the binary cache.
- PUMA depends on published MOOSE/nifti2dicom packages; their local source repairs
  require coordinated upstream releases before ordinary PyPI installs inherit them.
- The audit created no remote and rewrote no published history. Release candidates
  are prepared on the existing security branch; publishing is coordinated separately.

## Version 1.9.0 release candidate

- PyPI and GitHub tag availability were checked by the coordinating release agent.
- Metadata requires MOOSE >=3.3.0,<4 and nifti2dicom >=2.2.0 so package upgrades
  inherit the coordinated source repairs. Those releases must publish first.
- Source security suite: 14 passed. Source distribution and wheel builds pass;
  both archives were inspected and contain no local/imaging artifacts.
- Actual candidate wheels for PUMA 1.9.0, MOOSE 3.3.0 and nifti2dicom 2.2.0 were
  loaded from an isolated directory outside all repositories using the available
  ML dependency environment. Versions and import paths were checked. Real PUMA
  image-processing/conversion/visualization imports succeed, and both published
  console entrypoints (`pumaz --help`, `pumaz-display --help`) exit successfully.
- No feature was removed. Existing options remain exposed. Intentionally stricter
  behavior: native command failures stop processing; legacy binary caches refresh
  once; Python 3.10 is no longer supported. These changes are documented in README.
- This validates imports/CLI availability and synthetic security paths, not the
  full segmentation/registration pipeline, clinical accuracy or native Windows.

### Published binary archive compatibility

All five pinned upstream ZIP hashes were recomputed and matched. Each published
archive contains top-level `__MACOSX` AppleDouble metadata. The installer ignores
those members without writing them, then validates/extracts only expected bundle
members. A regression was observed failing before this compatibility repair.
All five actual archives were validated and extracted to private temporary
folders; both required binaries were present, with no metadata tree installed.
Selected member counts are Windows x86_64: 7; Linux x86_64: 7; Linux arm64: 4;
macOS x86_64: 7; macOS arm64: 7. Unexpected non-metadata roots remain rejected.
