
## Lava AMI Utility { data-toc-label="lava-ami" }

The **lava-ami** utility displays the available, lava compatible, AMIs and the
AMI specified in each lava worker CloudFormation stack.

??? Usage

    ```bare
    usage: lava-ami [-h] [-n N] [--sak] [--profile PROFILE] [-U] [-v] [-W]
                    [STACK-NAME ...]

    Manage the AMIs used in lava worker CloudFormation stacks.

    positional arguments:
      STACK-NAME         CloudFormation stack name for a lava worker. Glob style
                         patterns can be used. If not specified, or any of the
                         patterns is *, the -U / --update option is not permitted.

    optional arguments:
      -h, --help         show this help message and exit
      -n N               Only include specified number of most recent images of
                         each type in the selection list. Default 5.
      --profile PROFILE  As for AWS CLI.
      -U, --update       Initiate an interactive update process to allow a new AMI
                         to be applied for selected stacks. If specified, one or
                         more stack patterns must be specified (no single *) to
                         make it harder to maniacally update a whole bunch of
                         stacks in one go. You can thank me later.
      -v, --version      show program's version number and exit
      -W, --no-wait      Don't wait for CloudFormation stack updates to complete.
    ```

**Lava-ami** also provides an update mode that allows a (more or less)
interactive process to select and apply a different AMI to one or more lava
worker stacks. This process is a lot simpler and less error prone than trying to
manage the AMI used on multiple workers in the AWS CloudFormation console.

**Lava-ami** will silently ignore worker stacks that appear to be parasitic
workers hosted on another worker instance. These are detected by the absence of
a machine type or AMI ID parameter in the CloudFormation stack. If these need to
be updated, use the AWS CloudFormation console.

**Lava-ami** is conservative in its definition of lava compatibility for an AMI.
The lava worker itself can run on any Linux machine with the right prerequisite
components installed but these two images support the deployment and
bootstrapping processes preferred in lava operational environments.
**Lava-ami** will highlight the most recent lava AMI in its output.
