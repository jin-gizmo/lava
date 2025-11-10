
# Lava API Reference { x-nav="API" }

Lava has a relatively narrow client API that focuses on the connector
subsystem and a few generic utilities.

The API, which includes the main lava worker and all of
[the lava utilities](#lava-commands-and-utilities) is available on PyPI as the
`jinlava` package.

```bash
pip install jinlava

# Include support for PyGreSQL, the AWS Redshift driver, Pyodbc etc.
pip install 'jinlava[extras]'
```

The lava internals are (deliberately) not catalogued here to avoid distracting
those who are just interested in developing lava [exe](#job-type-exe), 
[pkg](#job-type-pkg) and [docker](#job-type-docker) payloads.

::: lava

::: lava.connection

::: lava.lib
    options:
      show_submodules: true

::: lava.version
    options:
      members:
        - SemanticVersion
        - version

