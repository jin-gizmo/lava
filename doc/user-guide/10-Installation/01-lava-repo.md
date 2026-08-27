

## The Lava Repo

### Getting Started with the Repo

The lava repo is available on [GitHub](https://github.com/jin-gizmo/lava).

After cloning the repo:

```bash
cd lava

# See what "make" can do ... this will print help
make

# Create the virtualenv and install required Python packages.
# This can be rerun as needed, even with an existing virtualenv.
make init

# Activate the virtualenv
source venv/bin/activate
```

Apart from a standard UNIX-like Python development environment, the following
additional tools are required:

| Tool  | Why it's needed                                              |
| ----------- | --- |
| [aspell](http://aspell.net)                                  | Spell checking the user guide. Install it on macOS with Homebrew. |
| [AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) | Used for deployment of lava components and various other things. |
| [docker](https://www.docker.com)                             | Cross platform builds, testing and building the [lava docker images](#building-the-lava-docker-images). [Docker Desktop](https://www.docker.com/products/docker-desktop/) is just fine. |
| [gh](https://cli.github.com) | The GitHub CL is used to create GitHub releases. |
| [packer](https://developer.hashicorp.com/packer)             | Building the [lava AMI](#the-lava-ec2-ami).                  |
| [shellcheck](https://www.shellcheck.net) | Used as part of pre-commit checks. Install it on macOS with Homebrew. |
| [tokei](https://github.com/XAMPPRocky/tokei)                 | Required to count lines of code (optional). Install it on macOS with Homebrew. |

!!! tip
    Running `make req` will do an automated check for prerequisites using the
    [req](https://github.com/jin-gizmo/req#req---a-software-prerequisite-checker--installer)
    gizmo.

The Oracle basic client and SQL*Plus are also required.
See [Oracle Client Binaries](#oracle-client-binaries).

### A Quick Tour of the Repo

```bare
lava
├── ami                     | Code and resources to build the lava AMI
│   ├── conf.d              | Reusable build script components
│   ├── deploy -> ../deploy |
│   ├── os                  | Build scripts for various target O/S
│   ├── resources           | Local resources used in the build
│   └── resources.s3        | Larger resources used in the build synced to S3
│   . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 
├── bin                     | Source for lava CLI utilities
├── cfn                     | CloudFormation templates (src only - see dist/cfn)
├── deploy                  | YAML config files for deploying into AWS accounts
│   . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 
├── dev-tools               | Makefile for building the lava job framework
│   . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 
├── dist                    | Ephemeral - created by build process (ex-repo)
│   ├── ami                 | Manifests produced by AMI builds
│   ├── cfn                 | CloudFormation templates ready to deploy
│   ├── dev-tools           | Lava job framework builds
│   ├── doc                 | Lava user guide builds
│   ├── jinlava             | Builds of the jinlava Python package
│   ├── lambda              | Lava Lambda function builds (zip files)
│   ├── pkg                 | Lava install package builds by O/S
│   ├── schemas             | Built versions of the lava JSON schemas
│   └── test                | Unit test coverage cache and reports
│   . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 
├── doc                     |
│   ├── img                 | Images referenced in the user guide
│   ├── img.src             | Legacy images that originate in a different format
│   ├── mkdocs              | Configuration for Material for MkDocs
│   └── templates           | lava job templates
│   └── user-guide          | Lava user guide source
│   . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 
├── docker                  | Source for building lava docker images
│   ├── common              | Common (O/S independent) build components
│   ├── os                  | O/S dependent build components
│   └── pkg                 | External packages required (e.g. Oracle)
│   . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 
├── etc                     | Tools & utilities needed to build / maintain lava
│   ├── boot                | Boot scripts for EC2 host running a lava worker
│   ├── builders            | Dockerfiles to build lava for foreign platforms
│   └── git-hooks           |
│   . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 
├── external-packages       | External non-Python packages that lava requires
│   └── oracle              | 
│   . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 
├── lambda                  | Source for the lava Lambda functions
│   ├── dispatch            |
│   ├── metrics             |
│   ├── s3trigger           |
│   └── stop                |
│   . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 
├── lava                    | Source for lava
│   ├── connection          | Lava connector handlers
│   ├── handlers            | Lava job type handlers
│   ├── lib                 | Miscellaneous library utilities
│   └── resources           | Lava job framework source
│   . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 
├── misc                    | Miscellaneous components, boot scripts etc
│   ├── boot                | Boot scriptlets called from root.boot.sh
│   ├── boot.optional       | Optional boot scriptlets
│   └── ssm                 | Legacy CFN for SSM command documents
│   . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 
├── schemas                 | Source for JSON schemas for jobs, connections etc.
│   . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 
└── test                    | Lava units tests and test jobs (gnarly)
    ├── checks              | Custom validation logic for lava test jobs
    ├── data                | Test data (e.g. used to populate test DBs)
    ├── integration         | Pytest handler for running / validating lava jobs
    ├── jobs                | Test jobs, connectors etc (lava job framework fmt)
    ├── services            | Data for Docker compose services used for testing
    └── unit                | Unit test source
```

!!! tip
    On macOS, you may want to add the `dist` and `external-packages` directories
    to the exclusion list for Time Machine backups. They can get pretty big and
    it's all ephemeral.
