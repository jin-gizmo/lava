# Lava Jobs

This directory contains YAML formatted templates for lava jobs. The templates
are Jinja rendered into final JSON objects placed in the `dist` directory.

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

Because the jobs themselves contain Jinja syntax intended for lava, the process
of preparing the jobs cannot use default Jinja delimiters. Instead, the
following are used:

*   `<{...}>` instead of `{{...}}`
*   `<#...#>` instead of `{#...#}`
*   `<%...%>` instead of `{% %}`
