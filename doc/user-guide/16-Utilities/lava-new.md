
## Lava-new Utility { data-toc-label="lava-new" }

!!! note
    New in v8.2 (Kīlauea).

The **lava-new** utility is used to create a new
[lava job framework](#the-lava-job-framework) project.

??? "Usage"

    ```bare
    usage: lava-new [-h] [-v] [--no-input] [-p KEY=VALUE] directory

    Create a new lava job framework project.

    positional arguments:
      directory             Create the template source in the specified directory
                            (which must not already exist).

    options:
      -h, --help            show this help message and exit
      -v, --version         show program's version number and exit
      --no-input            Do not prompt for user input. The -p / --param option
                            should be used to specify parameter values.
      -p KEY=VALUE, --param KEY=VALUE
                            Specify default parameters for the underlying
                            cookiecutter used to create the new lava project. Can
                            be used multiple times. Available parameters are
                            config_checks, description, docker_platform,
                            docker_prefix, environment, git_setup,
                            include_lava_libs, job_prefix, jupyter_support, owner,
                            payload_prefix, pip_index_url, project_dir,
                            project_name, realm, rule_prefix, s3trigger_prefix.
    ```
