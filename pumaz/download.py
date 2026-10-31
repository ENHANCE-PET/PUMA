#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------------------------------------------------------
# Author: Lalith Kumar Shiyam Sundar | Sebastian Gutschmayer
# Institution: Medical University of Vienna
# Research Group: Quantitative Imaging and Medical Physics (QIMP) Team
# Date: 04.07.2023
# Version: 0.1.0
#
# Description:
# This module downloads the necessary binaries and models for the pumaz.
#
# Usage:
# The functions in this module can be imported and used in other modules within the pumaz to download the necessary
# binaries and models for the pumaz.
#
# ----------------------------------------------------------------------------------------------------------------------

import hashlib
import os
import shutil
import zipfile
import stat
import tempfile
from pathlib import Path, PurePosixPath

import requests
from rich.console import Console
from requests import exceptions as requests_exceptions

from pumaz import constants

console = Console()


class BinaryDownloadError(RuntimeError):
    """Raised when registration binaries cannot be downloaded."""


class BinaryExtractionError(RuntimeError):
    """Raised when a downloaded archive cannot be extracted."""


def _expected_files_ready(expected_files: list[str] | None) -> bool:
    """Return True when all expected binaries exist and are executable."""
    if not expected_files:
        return False
    for path in expected_files:
        if not os.path.isfile(path):
            return False
        if not os.access(path, os.X_OK):
            return False
    return True


# Executable archives are small; reject resource-exhausting downloads/ZIPs.
MAX_DOWNLOAD_BYTES = 256 * 1024 * 1024
MAX_EXTRACTED_BYTES = 1024 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 10000


def _validated_members(archive: zipfile.ZipFile, parent: str, directory: str):
    """Validate every member before writing any archive content."""
    root = Path(parent).resolve()
    expected = Path(directory).relative_to(parent).as_posix()
    members = archive.infolist()
    if len(members) > MAX_ARCHIVE_MEMBERS or sum(m.file_size for m in members) > MAX_EXTRACTED_BYTES:
        raise BinaryExtractionError("Registration archive exceeds extraction limits.")
    for member in members:
        name = member.filename
        parts = PurePosixPath(name).parts
        mode = member.external_attr >> 16
        if (not parts or name.startswith("/") or "\\" in name or ":" in name
                or any(part in {".", ".."} for part in name.rstrip("/").split("/"))
                or parts[0] != expected
                or stat.S_IFMT(mode) not in {0, stat.S_IFREG, stat.S_IFDIR}):
            raise BinaryExtractionError(f"Unsafe registration archive member: {name!r}")
        destination = root.joinpath(*parts)
        if not destination.resolve().is_relative_to(root):
            raise BinaryExtractionError(f"Archive destination escapes binary cache: {name!r}")
        if any(path.is_symlink() for path in (destination, *destination.parents) if path != root):
            raise BinaryExtractionError(f"Symbolic link in archive destination: {name!r}")
    return members


def download(item_name: str, item_path: str, item_dict: dict, *, expected_files: list[str] | None = None) -> str:
    """
    Downloads the item (model or binary) for the current system.

    :param item_name: The name of the item to download.
    :type item_name: str
    :param item_path: The path to store the item.
    :type item_path: str
    :param item_dict: The dictionary containing item info.
    :type item_dict: dict
    :return: The path to the downloaded item.
    :rtype: str
    :raises: None

    This function downloads the item specified by `item_name` from the URL specified in the `item_dict` dictionary. It
    shows the download progress using the `rich` library and extracts the downloaded zip file using the `zipfile`
    library. Only a cache carrying the matching pinned-digest marker may skip downloading.
    Legacy installations are refreshed through verified staging before use.

    :Example:
        >>> download('registration_binaries', '/path/to/item', {'registration_binaries': {'url': 'http://example.com/binaries.zip', 'filename': 'binaries.zip', 'directory': 'binaries'}})
    """
    try:
        item_info = item_dict[item_name]
    except KeyError as exc:
        raise BinaryDownloadError(f"No registration binaries are packaged for {item_name!r}.") from exc
    root = Path(item_path)
    name = item_info["directory"]
    if not name or name in {".", ".."} or any(c in name for c in "/\\:"):
        raise BinaryDownloadError("Binary directory must be a single directory name.")
    expected_digest = item_info.get("sha256", "")
    if len(expected_digest) != 64 or any(c not in "0123456789abcdef" for c in expected_digest):
        raise BinaryDownloadError("A pinned SHA-256 checksum is required for registration binaries.")
    directory = root / name
    marker_name = ".puma-archive-sha256"
    if directory.is_symlink():
        raise BinaryExtractionError("Binary directory must not be a symbolic link.")
    marker = directory / marker_name
    if (marker.is_file() and not marker.is_symlink()
            and marker.read_text().strip() == expected_digest
            and (not expected_files or _expected_files_ready(expected_files))):
        return os.path.join(item_path, item_name)
    root.mkdir(parents=True, exist_ok=True)
    # Legacy installations are replaced with fresh files rather than retaining
    # old Windows Everyone:F ACLs. Staging never touches the executable cache.
    try:
        with tempfile.TemporaryDirectory(prefix=".puma-download-", dir=root) as stage_name:
            stage = Path(stage_name)
            archive = stage / "download.zip"
            digest = hashlib.sha256()
            received = 0
            response = requests.get(item_info["url"], stream=True, timeout=(10, 120))
            try:
                response.raise_for_status()
                with archive.open("wb") as stream:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        received += len(chunk)
                        if received > MAX_DOWNLOAD_BYTES:
                            raise BinaryDownloadError("Registration archive exceeds download limits.")
                        digest.update(chunk)
                        stream.write(chunk)
            finally:
                if hasattr(response, "close"):
                    response.close()
            if digest.hexdigest() != expected_digest:
                raise BinaryDownloadError("Registration archive SHA-256 checksum mismatch.")
            extracted = stage / "extracted"
            extracted.mkdir()
            with zipfile.ZipFile(archive) as zip_ref:
                members = _validated_members(zip_ref, str(extracted), str(extracted / name))
                for member in members:
                    zip_ref.extract(member, extracted)
            bundle = extracted / name
            if not bundle.is_dir():
                raise BinaryExtractionError("Archive lacks the required binary directory.")
            if expected_files:
                for expected in expected_files:
                    relative = Path(expected).relative_to(directory)
                    if not (bundle / relative).is_file():
                        raise BinaryExtractionError(f"Archive lacks required binary: {relative}")
            (bundle / marker_name).write_text(expected_digest + "\n")
            # Unlike staging, this backup has no automatic cleanup: failed
            # restoration must leave the user's old installation recoverable.
            backup = None
            if directory.is_symlink():
                raise BinaryExtractionError("Binary directory must not be a symbolic link.")
            if directory.exists():
                backup = Path(tempfile.mkdtemp(prefix=".puma-backup-", dir=root))
                try:
                    directory.rename(backup / "previous")
                except OSError:
                    backup.rmdir()
                    raise
            try:
                bundle.rename(directory)
            except OSError:
                if backup is not None:
                    try:
                        (backup / "previous").rename(directory)
                    except OSError as exc:
                        raise BinaryExtractionError(
                            f"Binary publication and restoration failed; old binaries preserved at {backup / 'previous'}."
                        ) from exc
                    backup.rmdir()
                raise
            if backup is not None:
                shutil.rmtree(backup)
    except requests_exceptions.RequestException as exc:
        raise BinaryDownloadError("Unable to download registration binaries; previous installation preserved.") from exc
    except (zipfile.BadZipFile, OSError) as exc:
        raise BinaryExtractionError("Unable to install verified registration binaries.") from exc
    console.print(" Registration binaries - download complete.", style=constants.PUMAZ_COLORS["success"])
    return os.path.join(item_path, item_name)
