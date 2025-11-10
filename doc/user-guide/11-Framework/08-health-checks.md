
## Health Checking Deployable Components { data-toc-label="Health Checking" }

See also [Maintaining DynamoDB Table Entries](#maintaining-dynamodb-table-entries).

### Code Hygiene

The lava job framework incorporates some basic code health checks. The checks
can be run using:

```bash
make check

# or ...

etc/git-hooks/pre-commit
```

The checks are also run prior to any installation process. Installation is
blocked if the checks fail.

If the framework was used to automatically initialise Git for the project then
the checking process is also configured as a pre-commit hook.

|Check Type|Tool|Description|
|---|--|--------------------|
|Python quality|[flake8](https://flake8.pycqa.org/en/latest/)|Performs a range of PEP8 compliance and other code health checks, including compliance with [black](https://github.com/psf/black) formatting. The configuration file for flake8 is contained in `.flake8` and for black in `pyproject.toml`.|
|YAML correctness|[yamllint](https://yamllint.readthedocs.io)|Performs correctness and style checks on the project YAML files. The configuration file is in `.yamllint.yaml`.|
|Config alignment|Builtin|Compares the key structures in the configuration files in the `config` directory and highlights any differences. Generally, configuration files for a project correlate to different target realms (e.g. test vs prod). While the configuration values will vary by environment, the key hierarchies should be identical. The only configuration option is the choice between `warning` and `strict` modes which is specified in `etc/git-hooks/pre-commit`.|

The following command will apply [black](https://github.com/psf/black)
formatting to project Python files:

```bash
make black

# or ...

black lava-payloads misc

# or even ...

black
```

### Configuration Drift Detection { data-toc-label="Drift Detection" }

Changes to a lava job framework based project should always be done via a `make
install` from an appropriately managed Git repo to ensure that the deployed
components are fully aligned with the committed contents of the repo.

Deviation from this practice can result in misalignment between deployed
components and the repo contents; aka *drift*.

The lava job framework supports drift detection for the DynamoDB table entries.
To detect differences between the repo contents and the deployed table entries,
run the following command:

```bash
make diff env=...
```

Note that fields starting with `x-` / `X-` are excluded from drift comparisons.
