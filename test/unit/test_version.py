"""Test lava version."""

import sys

import pytest  # noqa

from lava import version


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'semver,major,minor,patch',
    [
        ('1.11.111', 1, 11, 111),
        ('5.20.30', 5, 20, 30),
    ],
)
def test_semantic_version_ok(semver, major, minor, patch):
    v = version.SemanticVersion(semver)

    assert (v.major, v.minor, v.patch) == (major, minor, patch)
    assert str(v) == semver

    assert v > version.SemanticVersion('1.5.20')
    assert v >= version.SemanticVersion('1.5.20')
    assert v < version.SemanticVersion('9.10.20')
    assert v <= version.SemanticVersion('9.10.20')
    assert v != version.SemanticVersion('9.10.20')


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'semver',
    [
        '1.2',
        'x.y.z',
    ],
)
def test_semantic_version_bad(semver):
    with pytest.raises(Exception, match='Bad semantic version'):
        version.SemanticVersion(semver)


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'args,expected',
    [
        ([], version.__version_num__),
        (['--all'], version.__version__),
        (['--name'], version.__version_name__),
    ],
)
def test_version_main(args, expected, monkeypatch, capsys):
    """Mock a command line run of version.py."""

    monkeypatch.setattr(sys, 'argv', ['version.py', *args])
    assert version.main() == 0
    assert capsys.readouterr().out.strip() == expected


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'args,expected',
    [
        (['--eq', '1.0.500'], 1),
        (['--ge', '1.0.500'], 0),
        (['--ge', version.__version_num__], 0),
        (['--ge', '1000.0.0'], 1),
    ],
)
def test_version_main_compare(args, expected, monkeypatch, capsys):
    """Mock a command line run of version.py."""

    monkeypatch.setattr(sys, 'argv', ['version.py', *args])
    assert version.main() == expected
