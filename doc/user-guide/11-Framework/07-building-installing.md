
## Building the Deployable Components { data-toc-label="Building" }

Once the lava components are created, the installable components are created
thus:

```bash
# cd to the project root directory then ...

# Activate the virtualenv
source venv/bin/activate

# Build the lava artefacts
make dist env=<ENV>
```

The value of the `env` parameter must correspond to one of the environment
configuration YAML files in the `config` directory.

The deployable components will be built and placed in the `dist/<ENV>`
directory.

## Installing Deployable Components { data-toc-label="Installing" }

The lava components can be installed using:

```bash
# cd to the project root directory then ...

# Activate the virtualenv
source venv/bin/activate

# Deploy the lava artefacts
make install env=<ENV>
```

This will do the following:

1.  Build any out of date artefacts.

2.  Perform some basic pre-installation checks (e.g. verify permission to write
    to the payloads area in S3).
    
3.  Backup any existing payloads in the realm S3 bucket under the `__bak__`
    prefix.
    
4.  Deploy the DynamoDB table entries and payload components.

!!! warning
    No backup is made of existing DynamoDB entries prior to uploading new ones.

To perform an installation without the pre-installation checks use:

```bash
# Deploy the lava artefacts without pre-install checks.
make _install env=<ENV>
```

## Uninstalling Deployable Components { data-toc-label="Uninstalling" }

The lava components can be uninstalled using:

```bash
# cd to the project root directory then ...

# Activate the virtualenv
source venv/bin/activate

# Remove the lava artefacts
make uninstall env=<ENV>
```

To clean up the local `dist` area:

```bash
# cd to the project root directory then ...

make clean
```
