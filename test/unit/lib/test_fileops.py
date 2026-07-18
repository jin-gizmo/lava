"""Test fileops utils."""

from pathlib import Path

import pytest  # noqa

from lava.lib.fileops import *


# ------------------------------------------------------------------------------
def test_makedirs(tmpdir):
    dirname = os.path.join(tmpdir, 'test')
    makedir(dirname)
    makedir(dirname)
    # Create an empty file
    filename = os.path.join(dirname, 'file')
    with open(filename, 'w'):
        pass

    with pytest.raises(Exception, match='exists but is not a directory'):
        makedir(filename)


# ------------------------------------------------------------------------------
def test_deletefiles(tmpdir):
    dirname = os.path.join(tmpdir, 'testdelete')
    makedir(dirname)

    # Create some files
    files = [os.path.join(dirname, f'file{n}') for n in range(3)]
    for f in files:
        with open(f, 'w') as fp:
            print(f'File: {f}', file=fp)
    delete_files(*files)

    # Delete a non-existent file
    delete_files(os.path.join(dirname, 'no-such-file'))

    # Pass over empty file names
    delete_files('')

    # Force a delete to fail by removing write perm on the directory
    with open(files[0], 'w'):
        pass
    os.chmod(dirname, 0o500)
    with pytest.raises(Exception, match='Could not delete'):
        delete_files(files[0])
    os.chmod(dirname, 0o700)


# ------------------------------------------------------------------------------
def test_fsplit_no_delete(tmpdir, td):

    # Source file has 12 lines of 31 chars (including \n)

    splits = list(
        fsplit(
            str(td / 'whatever.txt'), prefix=os.path.join(tmpdir, 't1-'), maxsize=31, suffixlen=2
        )
    )
    assert len(splits) == 12
    assert Path(splits[6]).read_text() == '7   abcdefghijklmnopqrstuvwxyz\n'

    # Check out lines too long to split
    with pytest.raises(Exception, match=r'line \d+ is too long'):
        list(
            fsplit(
                str(td / 'whatever.txt'), prefix=os.path.join(tmpdir, 't2-'), maxsize=1, suffixlen=2
            )
        )

    # Specified suffix too small to hold 10 files but fsplit detects and fixes
    list(
        fsplit(
            str(td / 'whatever.txt'), prefix=os.path.join(tmpdir, 't5-'), maxsize=31, suffixlen=1
        )
    )


def test_fsplit_delete(tmp_path, td):

    # Make a copy of our source file.
    srcfile = tmp_path / 'copy.txt'
    srcfile.write_text((td / 'whatever.txt').read_text())
    list(fsplit(str(srcfile), prefix=str(tmp_path / 't3-'), maxsize=31, suffixlen=2, delete=True))
    assert not srcfile.exists()


def test_fsplit_cannot_split(tmp_path, td):

    # Make a copy of our source file to clash with name of a split.
    srcfile = tmp_path / 't4-01'
    srcfile.write_text((td / 'whatever.txt').read_text())
    with pytest.raises(Exception, match='chunk will overwrite original'):
        list(fsplit(str(srcfile), prefix=str(tmp_path / 't4-'), maxsize=31, suffixlen=2))


# ------------------------------------------------------------------------------
def test_lockfile(tmp_path):

    lockf = str(tmp_path / 'lock')
    assert lock_file(lockf)


# ------------------------------------------------------------------------------
@pytest.mark.parametrize('pkg', ['little.zip', 'little.tar', 'little.tar.bz2'])
def test_unpack_ok(pkg, tmp_path, td):
    unpack(str(td / pkg), str(tmp_path))


def test_unpack_fail():
    with pytest.raises(Exception, match='Cannot unpack'):
        unpack('nosuchpkg.zip', 'nosuchdir')

    with pytest.raises(Exception, match='Don\'t know how to unpack'):
        unpack('unrecognised.suffix', 'somedir')


# ------------------------------------------------------------------------------
def test_read_head_or_tail(td):
    srcfile = str(td / 'whatever.txt')

    # Read head
    assert read_head_or_tail(srcfile, 31) == '1   abcdefghijklmnopqrstuvwxyz\n'
    # Read tail
    assert read_head_or_tail(srcfile, -31) == '12  abcdefghijklmnopqrstuvwxyz\n'
    # Read nothing
    assert read_head_or_tail(srcfile, 0) == ''


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'value, expected',
    [
        ('abcd', 'abcd'),
        ('.abcd', 'abcd'),
        ('../abcd', 'abcd'),
        ('a"bcd', 'abcd'),
        ("a'bcd", 'abcd'),
        ('ab    cd', 'ab-cd'),
        ('ab\tcd', 'ab-cd'),
        ('#!abcd', 'abcd'),
    ],
)
def test_sanitise_filename(value, expected):
    assert sanitise_filename(value) == expected
