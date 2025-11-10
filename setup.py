"""setup.py for jinlava."""

from __future__ import annotations

import json
from itertools import chain
from pathlib import Path

from packaging.version import Version
from setuptools import find_packages, setup

REPO_URL = 'https://github.com/jin-gizmo/lava'
REQUIRES_PYTHON = '>=3.11.0'
VERSION = str(
    Version(
        json.loads((Path(__file__).parent / 'lava' / 'VERSION.json').read_text(encoding='utf-8'))[
            '__version_num__'
        ]
    )
)


# ------------------------------------------------------------------------------
def looks_like_script(path: Path) -> bool:
    """Check if a file looks like a script."""

    # noinspection PyUnboundLocalVariable
    if not (path.is_file() and (stat := path.stat()).st_size > 2 and stat.st_mode & 0o100):
        return False

    with open(path) as _fp:
        return _fp.read(2) == '#!'


# ------------------------------------------------------------------------------
def find_scripts(*dirs: str) -> list[str]:
    """Find all executable scripts in the specified directory."""

    return [str(f) for f in chain(*(Path(d).glob('*') for d in dirs)) if looks_like_script(f)]


# ------------------------------------------------------------------------------
# Import README.md and use it as the long-description. Must be in MANIFEST.in
with open('PYPI.md') as fp:
    long_description = '\n' + fp.read()

# ------------------------------------------------------------------------------
# Get pre-requisites from requirements.txt. Must be in MANIFEST.in
with open('requirements.txt') as fp:
    required = [s.strip() for s in fp.readlines()]

# Optional extras
with open('requirements-extra.txt') as fp:
    extras = [s.strip() for s in fp.readlines()]

# ------------------------------------------------------------------------------
setup(
    name='jinlava',
    version=VERSION,
    packages=find_packages(exclude=['tests', '*.tests', '*.tests.*', 'tests.*']),
    url=REPO_URL,
    scripts=find_scripts('bin'),
    license='BSD-3-Clause',
    author='Murray Andrews, Chris Donoghue, Alex Bool',
    description='AWS based distributed scheduler and job runner',
    long_description=long_description,
    long_description_content_type='text/markdown',
    platforms=['macOS', 'Linux'],
    python_requires=REQUIRES_PYTHON,
    install_requires=required,
    extras_require={'extras': extras},
    include_package_data=True,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'Natural Language :: English',
        'Operating System :: MacOS',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Utilities',
    ],
)
