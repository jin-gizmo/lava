"""Tests for lava/lava.py."""

from __future__ import annotations

from functools import lru_cache

import pytest

import lava.lavacore
from lava.lava import *
from lava.lib.aws import s3_split
import lava.config

REALMS_TABLE = boto3.Session().resource('dynamodb').Table('lava.realms')


# ------------------------------------------------------------------------------
@lru_cache
def get_s3_object_size(name: str) -> int:
    """Get size of an S3 object."""
    bucket_name, key = s3_split(name)
    bucket = boto3.Session().resource('s3').Bucket(bucket_name)
    return bucket.Object(key).content_length


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'version, payload, expected',
    [
        ('v1', 'mktmp.py', ['mktmp.py']),
        ('v1', 'mktmp.sh', ['mktmp.sh']),
        ('v2', 'mktmp.py', ['mktmp.py']),
        ('v2', 'mktmp.sh', ['mktmp.sh']),
    ],
)
def test_get_payload_from_s3_ok(
    version: str, payload: str, expected: list[str], monkeypatch, tc, tmp_path, realm_info
):
    """This should work with both the v1 and v2 downloader."""
    monkeypatch.setitem(lava.config.__config__, 'PAYLOAD_DOWNLOADER', version)
    payload_files = get_payload_from_s3(f'{tc.prefix.payload}/{payload}', realm_info, str(tmp_path))
    assert len(payload_files) == len(expected)
    for payload_file, expected_file in zip(sorted(payload_files), sorted(expected)):
        p = Path(payload_file)
        assert p.is_file()
        assert p.stat().st_size == get_s3_object_size(
            f'{realm_info.s3_payloads}/{tc.prefix.payload}/{expected_file}'
        )


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'payload, expected',
    [
        ('mktmp.py', ['mktmp.py']),
        ('mktmp.sh', ['mktmp.sh']),
    ],
)
def test_get_payload_from_s3_v1_ok(payload: str, expected: list[str], tc, tmp_path, realm_info):
    payload_files = get_payload_from_s3_v1(
        f'{tc.prefix.payload}/{payload}', realm_info.data, str(tmp_path)
    )
    assert len(payload_files) == len(expected)
    for payload_file, expected_file in zip(sorted(payload_files), sorted(expected)):
        p = Path(payload_file)
        assert p.is_file()
        assert p.stat().st_size == get_s3_object_size(
            f'{realm_info.s3_payloads}/{tc.prefix.payload}/{expected_file}'
        )


# ------------------------------------------------------------------------------
@pytest.mark.parametrize('payload', ['mktmp.py', 'mktmp.sh'])
def test_get_payload_from_s3_v1_too_big_fail(payload: str, tc, tmp_path, realm_info):
    payload_d = tmp_path / 'payload'
    payload_d.mkdir()
    with pytest.raises(LavaError, match=r'Payload size \d+ exceeds maximum'):
        get_payload_from_s3_v1(
            f'{tc.prefix.payload}/{payload}', realm_info.data, str(payload_d), max_size=1
        )


# ------------------------------------------------------------------------------
@pytest.mark.parametrize('payload', ['none-such', 'none-such/'])
def test_get_payload_from_s3_v1_no_files_fail(payload: str, tc, tmp_path, realm_info):
    payload_d = tmp_path / 'payload'
    payload_d.mkdir()
    with pytest.raises(LavaError, match='No payload files downloaded from S3'):
        get_payload_from_s3_v1(
            f'{tc.prefix.payload}/{payload}', realm_info.data, str(payload_d), max_size=1
        )


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'payload, expected',
    [
        ('mktmp.py', ['mktmp.py']),
        ('mktmp.sh', ['mktmp.sh']),
        ('mktmp', ['mktmp.py', 'mktmp.sh']),
    ],
)
def test_get_payload_from_s3_v2_ok(payload: str, expected: list[str], tc, tmp_path, realm_info):
    payload_files = get_payload_from_s3_v2(
        f'{tc.prefix.payload}/{payload}', realm_info.data, str(tmp_path)
    )
    assert len(payload_files) == len(expected)
    for payload_file, expected_file in zip(sorted(payload_files), sorted(expected)):
        p = Path(payload_file)
        assert p.is_file()
        assert p.stat().st_size == get_s3_object_size(
            f'{realm_info.s3_payloads}/{tc.prefix.payload}/{expected_file}'
        )


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'payload',
    ['mktmp.py', 'mktmp.sh', 'mktmp'],
)
def test_get_payload_from_s3_v2_too_big_fail(payload: str, tc, tmp_path, realm_info):
    payload_d = tmp_path / 'payload'
    payload_d.mkdir()
    with pytest.raises(LavaError, match=r'Payload size \d+ exceeds maximum'):
        get_payload_from_s3_v2(
            f'{tc.prefix.payload}/{payload}', realm_info.data, str(payload_d), max_size=1
        )


# ------------------------------------------------------------------------------
@pytest.mark.parametrize('payload', ['none-such', 'none-such/'])
def test_get_payload_from_s3_v2_no_files_fail(payload: str, tc, tmp_path, realm_info):
    payload_d = tmp_path / 'payload'
    payload_d.mkdir()
    with pytest.raises(LavaError, match='No payload files downloaded from S3'):
        get_payload_from_s3_v2(
            f'{tc.prefix.payload}/{payload}', realm_info.data, str(payload_d), max_size=1
        )


# ------------------------------------------------------------------------------
@pytest.mark.parametrize('job_type', ['exe', 'pkg', 'cmd'])
def test_get_job_handler_ok(job_type: str):
    handler = get_job_handler(job_type)
    assert callable(handler)


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'job_type, exc, match',
    [
        ('nonesuch', LavaError, 'Unknown job type'),
        # This is really an internal error ...
        ('__init__', LavaError, r'Bad job handler -- no run\(\) function'),
    ],
)
def test_get_job_handler_fail(job_type: str, exc, match: str):
    with pytest.raises(exc, match=match):
        get_job_handler(job_type)
