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

- 13 security regressions pass, with observed failures before the corresponding
  fixes. Tests execute synthetic native tools and workflow Bash, exercise
  integrity/path checks, legacy cache refresh and single/double rollback failures.
- Parent independent PUMA source review: GO; independently reran 13 tests.
- Fresh Python 3.11 dependency resolution succeeds with the final constraints.
- Final Python 3.11 resolved graph: pip-audit checked 112 packages, none skipped,
  and reported no known vulnerabilities. Source distribution and wheel builds pass.
- `git diff --check` passes. No ML runtime or real registration was executed.

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
- No remote, push, PR, release or merge was performed.
