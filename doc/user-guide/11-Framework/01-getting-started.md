
## Getting Started

Ensure you have GNU **make** and Python 3.9+ installed. Make will be
preinstalled on many Linux systems, or will be available in the distro package
repos. For macOS, install the Xcode developer tools.

=== "Recommended Approach"

    !!! note "New in v8.2 (Kīlauea)"

    The recommended approach to creating a new lava framework project is using
    the [lava-new](#lava-new-utility) utility.

    ```bash
    # Install the jinlava package if not already installed.
    pip install --user jinlava

    # Create a new lava framework project.
    lava-new my-project-directory
    ```

    ----


=== "Legacy Approach"

    The lava framework itself is packaged as a zip file:
    `cookiecutter-lava-<VERSION>.zip`. If this is not available, it can be
    built by cloning the lava repo and running `make tools`. The zip file will
    be placed in the `dist/dev-tools` directory.

    !!! note
        This was the approach required prior to v8.2 (Kīlauea). It can still be
        used provided you have access to the lava framework cookiecutter bundle.

    ```bash
    # Install cookiecutter 
    pip install --user --upgrade cookiecutter

    # Install the AWS CLI, if not installed.
    pip install --user --upgrade awscli

    # Create a new lava project. Cookiecutter will issue prompts for a few
    # configuration parameters. The parameters "project_name" and "project_dir"
    # are particularly important. The others can easily be changed later.

    cookiecutter cookiecutter-lava-<VERSION>.zip
    ```

    ----

Either approach will prompt the user for some basic configuration options and
then create the project structure in the specified directory. It should look
like this (items in angled brackets refer to the values provided in response to
cookiecutter prompts):

```
<project_dir>/
        +--> Makefile               # Master make file. Try "make help".
        +--> bin/                   # Miscellaneous utilities.
        +--> config/                # Config files - one per environment.
        |       +--> <env>.yaml     # Initial config built by cookiecutter.
        +--> etc/                   # Miscellaneous support files.
        +--> lava-connections/      # Lava connection specifications.
        +--> lava-jobs/             # Lava job specifications.
        +--> lava-payloads/         # Lava job payloads.
        +--> lava-rules/            # Amazon EventBridge specifications.
        +--> lava-triggers/         # Lava s3trigger specifications.
        +--> misc/                  # Non-deployable job related components.
```

To complete the setup:

```bash
# cd to the new project directory
cd <project_dir>

# Initialise the project environment. This will create a virtualenv and install
# a bunch of required components. This can be safely rerun at any time.
make init

# Activate the virtual environment
source venv/bin/activate
```
If the project requires any non-standard Python packages, create a suitable
`requirements.txt` file at the root of the project directory before running
`make init`. The packages required by the framework itself are already
covered in `etc/requirements.txt`.

The project is now ready to start creating the various lava components.
