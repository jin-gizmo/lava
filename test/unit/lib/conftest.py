"""Pytest config."""

from __future__ import annotations

from pathlib import Path

import pytest  # noqa

from test.const import REALM

SMB_SHARED_DIR = Path(__file__).parent.parent.parent / 'services/smb/share.x'


# ------------------------------------------------------------------------------
@pytest.fixture(scope='session')
def dynamo_json():
    """Sample Dynamo format object and its Python equivalent."""
    return (
        # Marshalled (ie DynamoDB format)
        {
            'realm': {'S': REALM},
            'x-workers': {'M': {'core': {'M': {'threads': {'N': '3'}, 'workers': {'S': 'core'}}}}},
            'config': {
                'M': {
                    'A_STRING': {'S': '1m'},
                    'A_BOOL_TRUE': {'BOOL': True},
                    'A_BOOL_FALSE': {'BOOL': False},
                    'A_FLOAT': {'N': '33.3'},
                    'INT_POS': {'N': '123'},
                    'INT_NEG': {'N': '-1024'},
                }
            },
        },
        # Unmarshalled i.e. Python conventional
        {
            'realm': REALM,
            'x-workers': {'core': {'threads': 3, 'workers': 'core'}},
            'config': {
                'A_STRING': '1m',
                'A_BOOL_TRUE': True,
                'A_BOOL_FALSE': False,
                'A_FLOAT': 33.3,
                'INT_POS': 123,
                'INT_NEG': -1024,
            },
        },
    )


# ------------------------------------------------------------------------------
@pytest.fixture(scope='session')
def secure_bucket() -> str:
    """Bucket with server logging enabled, encrypted etc."""
    return 'lava'


@pytest.fixture(scope='session')
def unlogged_bucket() -> str:
    """Bucket without server logging enabled."""
    return 'log'


@pytest.fixture(scope='session')
def no_such_bucket() -> str:
    """Bucket without server logging enabled."""
    return 'no-such-bucket'


# ------------------------------------------------------------------------------
@pytest.fixture(scope='session')
def smb_shared_dir(dirs) -> Path:
    """Get the SMB dir shared between the SMB container and host."""
    return dirs.smb_share


# ------------------------------------------------------------------------------
@pytest.fixture(scope='session')
def smb_hello_file(dirs) -> str:
    """Get the contents of the hello.txt file on our local SMB service."""

    return (dirs.smb_share / 'lava/hello.txt').read_text()
