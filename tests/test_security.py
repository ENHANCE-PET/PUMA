"""Synthetic security regressions; no imaging data or ML runtime required."""
import ast
import hashlib
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest


def registration_code():
    # Image registration shells out to native tools; unrelated ML imports are heavy.
    path = Path(__file__).parents[1] / 'pumaz' / 'image_processing.py'
    tree = ast.parse(path.read_text())
    selected = [node for node in tree.body if isinstance(node, (ast.ClassDef, ast.FunctionDef))
                and node.name in {'ImageRegistration', 'rgb2gray'}]
    namespace = dict(os=os, pathlib=__import__('pathlib'), subprocess=subprocess,
                     logging=logging, sys=sys, re=__import__('re'),
                     GREEDY_PATH='', C3D_PATH='', RED_WEIGHT=0.299,
                     GREEN_WEIGHT=0.587, BLUE_WEIGHT=0.114)
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), 'exec'), namespace)
    return namespace


@pytest.fixture
def native_tool(tmp_path):
    executable = tmp_path / 'native tool'
    record = tmp_path / 'arguments.jsonl'
    executable.write_text(f'#!{sys.executable}\nimport json, sys\n'
                          f'with open({str(record)!r}, "a") as f: f.write(json.dumps(sys.argv[1:])+"\\n")\n')
    executable.chmod(0o700)
    return executable, record


@pytest.mark.parametrize('operation', ['rigid', 'affine', 'deformable', 'resample', 'rgb2gray'])
def test_native_commands_preserve_filenames_without_executing_shell(tmp_path, native_tool, operation):
    namespace = registration_code()
    executable, record = native_tool
    namespace.update(GREEDY_PATH=str(executable), C3D_PATH=str(executable))
    marker = tmp_path / 'injected'
    malicious = f'image; touch {marker}; #.nii.gz'
    if operation == 'rgb2gray':
        namespace['rgb2gray'](malicious, 'output with spaces.nii')
    else:
        aligner = namespace['ImageRegistration'](malicious, '100x50x10', fixed_mask='mask with spaces.nii')
        aligner.set_moving_image('moving image.nii')
        if operation == 'resample':
            aligner.resample('output with spaces.nii', 'deformable', 'seg image.nii', 'out seg.nii')
        else:
            getattr(aligner, operation)()
    assert not marker.exists()
    arguments = [json.loads(line) for line in record.read_text().splitlines()]
    assert any(malicious in call for call in arguments)
    if operation in {'rigid', 'affine', 'deformable'}:
        assert all('mask with spaces.nii' in call for call in arguments)
    if operation == 'resample':
        assert arguments == [['-d', '3', '-rf', malicious, '-ri', 'LINEAR', '-rm',
                              'moving image.nii', 'output with spaces.nii', '-ri',
                              'LABEL', '0.2vox', '-rm', 'seg image.nii', 'out seg.nii',
                              '-r', './moving image.nii_warp.nii.gz', '-r',
                              './moving image.nii_affine.mat']]


def test_release_tag_cannot_execute_shell(tmp_path):
    import yaml
    workflow = yaml.safe_load((Path(__file__).parents[1] / '.github/workflows/release.yml').read_text())
    step = workflow['jobs']['release-meta']['steps'][0]
    marker = tmp_path / 'workflow-injected'
    tag = f'$(touch {marker})'
    script = step['run'].replace('${{ github.event_name }}', 'workflow_dispatch').replace(
        '${{ github.event.release.tag_name }}', '').replace('${{ github.event.inputs.tag }}', tag)
    result = subprocess.run(['bash', '-c', script], env={**os.environ, 'RELEASE_TAG': tag,
                            'GITHUB_OUTPUT': str(tmp_path / 'output')}, capture_output=True)
    assert result.returncode != 0
    assert not marker.exists()


def test_binary_extraction_rejects_symlink_destination(tmp_path, monkeypatch):
    from pumaz import download
    outside = tmp_path / 'outside'
    outside.mkdir()
    cache = tmp_path / 'cache'
    cache.mkdir()
    (cache / 'binaries').mkdir()
    (cache / 'binaries' / 'nested').symlink_to(outside, target_is_directory=True)
    payload = tmp_path / 'archive.zip'
    with zipfile.ZipFile(payload, 'w') as archive:
        archive.writestr('binaries/nested/owned', b'overwrite')
    data = payload.read_bytes()
    class Response:
        headers = {'Content-Length': str(len(data))}
        def raise_for_status(self): pass
        def iter_content(self, **kwargs): yield data
    monkeypatch.setattr(download.requests, 'get', lambda *a, **kw: Response())
    # A missing different directory forces extraction into a cache containing a symlink.
    with pytest.raises(download.BinaryExtractionError):
        download.download('test', str(cache), {'test': {'url': 'https://example.invalid/binaries.zip',
                          'filename': 'download.zip', 'directory': 'new-binaries', 'sha256': hashlib.sha256(data).hexdigest()}})
    assert not (outside / 'owned').exists()


def test_download_rejects_wrong_checksum_before_extracting(tmp_path, monkeypatch):
    from pumaz import download
    payload = tmp_path / 'archive.zip'
    with zipfile.ZipFile(payload, 'w') as archive:
        archive.writestr('binaries/executable', b'untrusted')
    data = payload.read_bytes()
    class Response:
        headers = {'Content-Length': str(len(data))}
        def raise_for_status(self): pass
        def iter_content(self, **kwargs): yield data
    monkeypatch.setattr(download.requests, 'get', lambda *a, **kw: Response())
    cache = tmp_path / 'cache'
    with pytest.raises(download.BinaryDownloadError, match='checksum'):
        download.download('test', str(cache), {'test': {'url': 'https://example.invalid/a.zip',
                          'filename': 'download.zip', 'directory': 'binaries', 'sha256': '0' * 64}})
    assert not (cache / 'binaries').exists()


def test_windows_setup_does_not_grant_everyone_write_access(tmp_path, monkeypatch):
    from pumaz.file_utilities import set_permissions
    binary = tmp_path / 'greedy.exe'
    binary.write_bytes(b'synthetic executable')
    binary.chmod(0o700)
    def deny_acl_changes(command, **kwargs):
        raise AssertionError(f'Binary setup must preserve administrator-provisioned ACLs: {command}')
    monkeypatch.setattr(subprocess, 'check_call', deny_acl_changes)
    set_permissions(str(binary), 'windows')


@pytest.fixture
def binary_payload(tmp_path, monkeypatch):
    from pumaz import download
    archive = tmp_path / 'payload.zip'
    with zipfile.ZipFile(archive, 'w') as stream:
        stream.writestr('binaries/greedy.exe', b'verified fresh binary')
    data = archive.read_bytes()
    class Response:
        headers = {'Content-Length': str(len(data))}
        def raise_for_status(self): pass
        def iter_content(self, **kwargs): yield data
        def close(self): pass
    monkeypatch.setattr(download.requests, 'get', lambda *a, **kw: Response())
    cache = tmp_path / 'cache'
    bundle = cache / 'binaries'
    bundle.mkdir(parents=True)
    binary = bundle / 'greedy.exe'
    binary.write_bytes(b'legacy writable executable')
    binary.chmod(0o777)
    info = {'test': {'url': 'https://example.invalid/a.zip', 'filename': 'download.zip',
                    'directory': 'binaries', 'sha256': hashlib.sha256(data).hexdigest()}}
    return cache, binary, info


def test_ready_legacy_binary_is_replaced_with_verified_fresh_file(binary_payload):
    from pumaz import download
    cache, binary, info = binary_payload
    old_inode = binary.stat().st_ino
    download.download('test', str(cache), info, expected_files=[str(binary)])
    assert binary.read_bytes() == b'verified fresh binary'
    assert binary.stat().st_ino != old_inode
    assert binary.stat().st_mode & 0o022 == 0
    assert (binary.parent / '.puma-archive-sha256').read_text().strip() == info['test']['sha256']


def test_bad_refresh_preserves_legacy_binary(binary_payload):
    from pumaz import download
    cache, binary, info = binary_payload
    info['test']['sha256'] = '0' * 64
    with pytest.raises(download.BinaryDownloadError):
        download.download('test', str(cache), info, expected_files=[str(binary)])
    assert binary.read_bytes() == b'legacy writable executable'
    assert not list(cache.glob('.puma-download-*'))


def test_binary_publish_failure_restores_previous_install(binary_payload, monkeypatch):
    from pumaz import download
    cache, binary, info = binary_payload
    rename = Path.rename
    def fail_publish(self, destination):
        if self.parent.name == 'extracted':
            raise PermissionError('simulated publication failure')
        return rename(self, destination)
    monkeypatch.setattr(Path, 'rename', fail_publish)
    with pytest.raises(download.BinaryExtractionError):
        download.download('test', str(cache), info)
    assert binary.read_bytes() == b'legacy writable executable'


def test_binary_rollback_failure_retains_recoverable_backup(binary_payload, monkeypatch):
    from pumaz import download
    cache, binary, info = binary_payload
    rename = Path.rename
    def fail_publish_and_rollback(self, destination):
        if self.parent.name == 'extracted' or self.name == 'previous':
            raise PermissionError('simulated publication and rollback failure')
        return rename(self, destination)
    monkeypatch.setattr(Path, 'rename', fail_publish_and_rollback)
    with pytest.raises(download.BinaryExtractionError):
        download.download('test', str(cache), info)
    backups = list(cache.glob('.puma-backup-*/previous/greedy.exe'))
    assert len(backups) == 1
    assert backups[0].read_bytes() == b'legacy writable executable'


def test_binary_archive_installs_bundle_without_extracting_macos_metadata(tmp_path, monkeypatch):
    from pumaz import download
    archive = tmp_path / 'appledouble.zip'
    with zipfile.ZipFile(archive, 'w') as stream:
        stream.writestr('binaries/greedy.exe', b'verified binary')
        stream.writestr('__MACOSX/._binaries', b'AppleDouble metadata')
        stream.writestr('__MACOSX/binaries/._greedy.exe', b'AppleDouble metadata')
        stream.writestr('__MACOSX/../outside', b'must never extract ignored metadata')
    data = archive.read_bytes()
    class Response:
        def raise_for_status(self): pass
        def iter_content(self, **kwargs): yield data
        def close(self): pass
    monkeypatch.setattr(download.requests, 'get', lambda *a, **kw: Response())
    cache = tmp_path / 'cache'
    download.download('test', str(cache), {'test': {'url': 'https://example.invalid/a.zip',
                      'filename': 'a.zip', 'directory': 'binaries',
                      'sha256': hashlib.sha256(data).hexdigest()}})
    assert (cache / 'binaries' / 'greedy.exe').read_bytes() == b'verified binary'
    assert not list(cache.rglob('__MACOSX'))
    assert not list(cache.rglob('._*'))
    assert not (cache / 'outside').exists()
