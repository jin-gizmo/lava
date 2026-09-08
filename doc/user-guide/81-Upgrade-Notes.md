# Upgrade Notes

!!! note
    These notes attempt to cover the salient points, not every detail. Read the
    [release notes](#release-notes).


## Version 8.3.0 ([Mauna Loa](https://en.wikipedia.org/wiki/Mauna_Loa))

!!! info
    These notes relate to upgrading from v8.2 to v8.3.0.


### General

#### Degree of difficulty for upgrade / rollback

Easy.

#### What’s new?

Read the [release notes](#release-notes).

#### OK, but what’s the stuff I should be focused on?

These are the changes that are most likely to cause an issue, if there is one:

*   **TLS/SSL in database connectors:** There have been fairly significant
    improvements in TLS/SSL handling in the database connectors. These should be
    backward compatible with existing connections in a v8.2 environment. It
    would be a good idea to review database connection specs to uplift their
    TLS/SSL related attributes to the new v8.3.0 model once there is no
    possibility of needing to rollback to v8.2.

*   **Oracle connector:** The Oracle connector now uses the new
    [python-oracledb](https://oracle.github.io/python-oracledb/) driver instead
    of the obsolete cx_Oracle driver. See [Through Thick and
    Thin](#through-thick-and-thin) for the dreary tale about thick vs thin mode.
    The Oracle connector also supports TLS/SSL now. The process of managing the
    Oracle binaries when building docker images, AMIs etc has been improved as
    well.

*   **Dispatch:** An SQS queue has been introduced between the
    `lava-<REALM>-dispatch` SNS topic and the dispatch helper AWS Lambda
    function. See [The Dispatch Helper](#the-dispatch-helper) for more
    information. The v8.3.0 realm CloudFormation stack will make this adjustment.

Other stuff to note:

*   **Testing**: There has been a major uplift in test infrastructure and
    automation. Producing a new lava release with just Python dependency updates
    should be pretty quick and easy now.

*   **JSON schemas:** The [JSON schemas](#lava-json-schemas) for the DynamoDB
    table entries are now hosted on GitHub in conjunction with the user guide.
    Upgraded tools and lava job framework use these to improve schema compliance
    before, and after, deployment. They also work with IDEs for auto-completion
    / suggestion etc.

*   **SharePoint:** The SharePoint connector has not been modified in this
    release but it hasn’t been regression tested either. Anyone got a free
    SharePoint?

*   **Python 3.9**: This is considered dead from a lava perspective. Lava v8.3.0
    has not been tested with 3.9.

#### Is v8.3.0 backward compatible with v8.2

Yes.

#### Do any jobs, connections etc need to be modified to run under v8.3.0?

No.

However, once v8.3.0 is deployed, the database connection specs should be
reviewed to uplift their TLS/SSL related attributes to the new v8.3.0 model.
Also, there are new capabilities in the job framework and lava utilities to
improve job hygiene that should be used.

#### Where do I find lava bits and pieces?

The repo is on [GitHub](https://github.com/jin-gizmo/lava).

Pre-built stuff (no repo required):

*   **jinlava**: The lava Python package
    [jinlava](https://pypi.org/project/jinlava/) is on PyPI. `pip install
    jinlava` does the business. This includes all the lava utilities (including
    the worker), but it is not the way to create a production lava worker

*   **User guide**: This version hosted on
    [GitHub Pages](https://jin-gizmo.github.io/lava/) (including the JSON
    schemas) is the only available version. If you’re looking at anything
    else, you’re looking at the wrong thing.

*   **CloudFormation templates**: Ready to go versions of the templates are
    provided in the
    [release on GitHub](https://github.com/jin-gizmo/lava/releases).

*   **Lava job framework:** This is provided in the
    [release on GitHub](https://github.com/jin-gizmo/lava/releases). However,
    the recommended way to start a new project is using the
    [lava-new](#lava-new-utility) utility which is installed as part of
    [jinlava](https://pypi.org/project/jinlava/). The framework bundle is
    required to upgrade an existing project.

*   **Lava docker images:** These are hosted as
    [GitHub packages](https://github.com/jin-gizmo?tab=packages&repo_name=lava)
    (GHCR). `docker run -it --rm ghcr.io/jin-gizmo/lava/amzn2023/base`

Stuff you need to build from the repo using the makefile(s):

*   **Lava worker package:** The production lava worker deployment package is
    built from the repo as a self contained code bundle that the EC2 based
    workers self install from S3 when they boot. The package must match the
    operating system, machine architecture and Python version. The file name
    will look like this: `lava-8.3.0-amzn2023-py3.11-x86_64.tar.bz2`. The files
    are reasonably chunky (80M or so).

*   **Lava lambda code bundles**: A zip file for each of the 4 lambdas is built
    from the repo: *dispatch*, *metrics*, *s3trigger* and *stop*. These get put
    in S3 and the realm CloudFormation stack finds them there.

*   **Lava AMI:** The builder for this is in the repo.

### Infrastructure

#### Are there any infrastructure changes?

Yes. 

An SQS queue has been introduced between the `lava-<REALM>-dispatch` SNS topic
and the dispatch helper AWS Lambda function. This should be transparent to end
users.  See [The Dispatch Helper](#the-dispatch-helper) for more info.

#### Do I need to update the CloudFormation stacks from v8.2 to v8.3?

You don’t *have* to, but it is strongly recommended, preferably before updating
workers, lambda functions etc. Version 8.2 workers can run on v8.3
CloudFormation stacks and vice versa.

#### How do I know what CloudFormation version is deployed?

The v8.2 and v8.3 templates have a stack output that is the version.

#### Do I need to build the v8.3 lava AMI?

You don’t *have* to, but it is strongly recommended. A v8.2 worker can run on
the v8.3 AMI and vice versa but it’s a good idea to keep them in sync. The thing
to be wary of is the Oracle binaries that are built in to the AMI. These are
less important in v8.3 as they are only used for the Oracle CLI connector and
any Oracle connection specifying the non-default *thick* mode.

### The Lava Job Framework { data-toc-label="Lava Job Framework" }

#### What’s new?

Read the [release notes](#version-830-mauna-loa).

#### OK, but what’s the stuff I should be focused on?

The main changes relate to enhanced support for [utilising the JSON
schemas](#working-with-the-json-schemas) to provide syntax support in IDEs and
pre-install validation. The v8.3 framework will refuse to deploy some jobs that
v8.2 would have accepted because of schema non-compliance. Rightly so. Fix the
jobs.

#### Do I need to upgrade existing projects to use the v8.3 framework?

No. Generally speaking, any version of the framework can be used with any
version of lava.  However, the v8.3 improvements will improve deployment quality
and its a good idea to update the framework in existing projects when there is
occasion to revisit a deployment.

#### How do I update the framework in an existing project?

See [Updating the Framework in an Existing
Project](#updating-the-framework-in-an-existing-project)
in the user guide.

### Upgrading Lava to v8.3.0 { data-toc-label="Upgrading to v8.3.0" }

#### What’s the upgrade process?

It can vary a bit based on the target environment but the following is a
possible high level sequence of events.  Keep in mind that multiple versions of
lava code (worker and lambdas) can be safely sitting alongside each other in S3.
Same goes for lava AMI versions. Each realm / worker explicitly specifies the
versions of code it runs using configuration data. Rolling forwards / backwards
is generally a matter of changing the configuration and restarting something.

1.  Build everything
    * Lava AMI
    * Lava Worker package
    * Lava lambda functions

2.  Deploy the bits to S3 (`make deploy …`) — this doesn’t affect any running
    realm.

3.  Update the common and realm CloudFormation stacks for the target realm to
    v8.3. You can flip the lambda function versions to v8.3.0 at the same time.

4.  Update the worker CloudFormation stack. You can (optionally) flip the AMI
    version to the v8.3.0 one at the same time or do that later using the
    [lava-ami](#lava-ami-utility) utility.

5.  Update the realm entry in the realms table to tell the target worker to load
    v8.3.0.

6.  Use the worker auto scaling group to refresh the worker(s).

This order can be shuffled a bit, if necessary.

#### How do I rollback to v8.2.0?

*   **CloudFormation:** Grab the v8.2.0 CloudFormation templates from the GitHub
    releases area and deploy them.

*   **Lambda functions:** Update the realm CloudFormation stack (same template)
    and change the lambda version parameter.

*   **Lava worker version**: Update the realm entry in the realms table to point
    the worker back to v8.2.0 of the code and then, replace the worker.

*   **AMI:** Use the [lava-ami](#lava-ami-utility)utility to select a different
    AMI. The utility will update the worker CloudFormation stack for you. Then,
    replace the worker.
