# Lava Payloads

This directory contains lava payload components. They can be simple, single
file, payloads such as standalone Python scripts, shell scripts or SQL scripts
or they can be more complex bundles that require a build process for a lava
`pkg` job.

The `Makefile` must contain a build rule for each payload artefact.

Use make(1) from the parent directory to manage the build and install processes.

```bash
# Do this from the main directory

# Remove generated stuff
make clean

# Build the deployable objects in dist directory
make dist

# Deploy them. The env var must correspond to a YAML file in config dir.
make install env=prod

# Uninstall them
make uninstall env=prod

```

## Jinja Rendering

Some files are, by default Jinja rendered using the config file as a source of
variable definitions.

For consistency with other rendering in the build environment, use the same
non-standard Jinja delimiters as are used for jobs. i.e.:

*   `<{...}>` instead of `{{...}}`
*   `<#...#>` instead of `{#...#}`
*   `<%...%>` instead of `{% %}`
