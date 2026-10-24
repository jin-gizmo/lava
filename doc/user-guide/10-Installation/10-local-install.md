## Installing Lava Locally

Lava can be installed locally on machines with an operating system (Linux /
macOS).

There are two ways to do this:

1. [Local installation via pip](#local-installation-via-pip)
2. [Local installation via a lava install package](#local-installation-via-a-lava-install-package).

### Local Installation via pip { data-toc-label="Via pip" }

The lava package is available as a standard Python package that can be installed
using pip. This is handy when developing lava jobs using an IDE such as PyCharm.
Full API documentation is also available. 

```bash
pip install jinlava
```

!!! warning
    Be aware that there is another, unrelated, lava package out there. Just
    running `pip install lava` **will do the wrong thing** so the lava
    package is bundled as `jinlava`. Python imports still use `import lava`. If
    you need to use both this lava and the other one, you must have a most
    unusual use case.

Some optional modules are available as *extras*. The following
modules are in the extras:

*   PyGreSQL (pgdb)

*   AWS Redshift Driver

*   Pyodbc

To install everything, including the optional extras:

```bash
pip install "jinlava[extras]"
```

### Local Installation via a Lava Install Package { data-toc-label="Via a Lava Install Package" }

First, obtain (or [build](#building-lava-components)) the code bundle for the
target O/S and machine architecture. This will include the worker and all of the
[lava utilities](#lava-commands-and-utilities).

!!! info
    For macOS, the bundle name will look something like    
    `lava-8.0.0-darwin24-py3.11-arm64.tar.bz2`.

The installation process is then:

```bash
# Package name depends on lava version, O/S, Python version
# and platform architecture.
PKG=lava-8.0.0-darwin24-py3.11-arm64.tar.bz2

# Extract the installer from the pkg.
tar xf $PKG install.sh

# Get help on the installer
./install.sh

# Do a clean install in the default location (/usr/local)
./install.sh -c $PKG

# See if it works. Make sure /usr/local/bin is in your path.
lava-version
```
