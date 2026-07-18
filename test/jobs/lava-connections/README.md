# Lava Connections

This directory contains YAML formatted templates for lava connection
specifications. The templates are Jinja rendered into final JSON formatted
objects placed in the `dist` directory.

Use make(1) from the parent directory to manage the job specifications.

```bash
# Do this from the main directory

# Remove generated stuff
make clean env=prod

# Build the deployable objects in dist directory
make dist env=prod

# Deploy them. The env var must correspond to a YAML file in config dir.
make install env=prod

# Uninstall them
make uninstall env=prod

```

## Jinja Rendering

The YAML templates are Jinja rendered using the config file as a source of
variable definitions.

For consistency with other rendering in the build environment, use the same
non-standard Jinja delimiters as are used for jobs. i.e.:

*   `<{...}>` instead of `{{...}}`
*   `<#...#>` instead of `{#...#}`
*   `<%...%>` instead of `{% %}`
