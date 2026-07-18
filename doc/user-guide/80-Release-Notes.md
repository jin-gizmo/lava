
# Release Notes

!!! note
    The historical release notes have been purged, because, well, who cares?
    The headers have been retained for old times sake.

## Warnings

The following changes will occur in the next major release after Version 8.

* The legacy `main` parameter will be removed from the [pkg](#job-type-pkg)
  job type. Use `command` instead.

* The legacy `key` parameter will be removed from the
  [redshift_unload](#job-type-redshift_unload) job type. Use `prefix` instead.

* The lava worker will perform much more aggressive validation of DynamoDB
  entries (jobs, actions, connections, etc.) as per the documentation. For
  example, jobs that would previously have run with a malformed action
  specification will be rejected prior to running.
  See [The Lava Schema Utility](#lava-schema-utility).

## Version 8

#### Version 8.3.0 ([Mauna Loa](https://en.wikipedia.org/wiki/Mauna_Loa))

This release includes reasonable subset of the lava testing components. Credit
and thanks to James Nguyen for a lot of effort to bring all this together into
a more consistent framework.

*   SSL/TLS handling has been improved across most of the database connectors. 
    Previously, SSL could be enabled for the more common database connectors but
    certificate validation and hostname validation were left to the vagaries of
    the underlying driver defaults. SSL/TLS validation can now be explicitly
    specified in the connection specification. The legacy `ssl` and `ca_cert`
    parameters are still supported but are now deprecated. Use `ssl_ca_file` and
    `ssl_mode` instead. See
    [SSL/TLS for Database Connectors](#ssltls-for-database-connectors) and
    individual connector entries for more information.

*   A number of backward compatible changes have been made to the
    [oracle](#connector-type-oracle) connector:

    *   The obsolete `cx_Oracle` driver has been replaced with its successor,
        [python-oracledb](https://oracle.github.io/python-oracledb/). `Oracledb`
        can operate in either *thin* or *thick* mode. The default thin mode does
        not require the Oracle client libraries whereas thick mode does.
        `Cx_Oracle` only supported thick mode. Nevertheless, the [lava
        AMI](#the-lava-ec2-ami) and *full* [lava docker
        images](#docker-images-for-lava) still contain the Oracle client
        libraries as they are required for the **SQL\*Plus** CLI used by the
        [sqlc](#job-type-sqlc) job type.

        The lava worker will use thin mode by default but can be configured to
        use thick mode.  See [Configuration for the oracle
        Connector](#configuration-for-the-oracle-connector).

        Programs using the lava API can request thick mode for themselves, if
        required, and provided they are run on a platform that has the client
        libraries installed.

    *   The [db_from_s3](#job-type-db_from_s3) job type accepts additional copy
        arguments for Oracle connections. Any NLS session parameter can now be
        set. This is particularly helpful for loading things such as date and
        time related data.

    *   The [oracle](#connector-type-oracle) connector now supports 
        [database client application identification](#database-client-application-identification).

    *   The [oracle](#connector-type-oracle) connector now supports SSL/TLS.   

*   Python package dependency versions have been updated. This includes a
    [pg8000](https://codeberg.org/tlocke/pg8000) update to fix
    [CVE-2025-61385](https://nvd.nist.gov/vuln/detail/CVE-2025-61385).

*   A number of changes have been made to the construction and handling of the
    [JSON schemas](#lava-json-schemas) for the [DynamoDB table](#dynamodb-tables)
    items:

    *   Previously, these schemas were essentially *built in* to the
        [lava-schema](#lava-schema-utility) utility and all but inaccessible for
        other purposes. They are now [hosted on GitHub](#lava-json-schemas) in
        both JSON and YAML formats and should be referenced by URL.

    *   The [lava-schema](#lava-schema-utility) utility is now a standalone
        utility that can be used on the DynamoDB tables and on local files.

    *   The [lava job framework](#the-lava-job-framework) has enhanced support
        for [utilising the JSON schemas](#working-with-the-json-schemas)
        to provide syntax support in IDEs and pre-install validation.
        To run the checks manually:
        ```bash
        make dist pre-install env=<ENV>
        ```

    *   The [lava job framework samples](#lava-job-framework-samples) have been
        updated to include a `$schema` line pointing to the applicable hosted
        schema. This enables improved syntax support by IDEs. To add `$schema`
        entries to an existing project:    
        ```bash
        make set-schema
        ```

    *   The schema for lava jobs will now object to `from` / `to` values without
        timezones in [schedule specifications](#schedule-specifications). The
        lava worker retains the older, less strict, behaviour, for now.

    *   The schemas now require the `owner` and `description` fields to be 
        provided for DynamoDB entries. Once again, the lava worker retains its
        zen on this, for now.

    *   Corrected some minor issues in the schema definitions.

*   The [rm](#removing-a-lava-state-item) (remove) subcommand has been added to
    the [lava state utility](#lava-state-utility). There is a new corresponding
    item in the [state API][lava.lib.state].

*   An additional [tojson](#tojson) function has been added to the
    [Jinja utility functions](#jinja-utility-functions) provided to the Jinja
    runtime renderer. Unlike the Jinja built-in
    [tojson](https://jinja.palletsprojects.com/en/stable/templates/#jinja-filters.tojson)
    filter (which is still available), the lava utility function can handle data
    types such as datetime.

*   Some minor usability improvements have been made to the
    [lava job framework](#the-lava-job-framework). This includes better support
    for using external Docker registries for [docker](#job-type-docker) job
    payloads as an alternative to ECR for the vanishingly rare circumstances
    in which this is a good idea.

*   No further testing has, or will, be done on Python versions prior to 3.11.
    No (known) breaking changes have been introduced but you are now on your tod.

*   Python 3.14 (with GIL enabled) is supported.

*   The process of building the docker images for foreign builds is now much
    faster. See [Building the Lava Worker Bundle for a Foreign
    Host](#building-the-lava-worker-bundle-for-a-foreign-host).

*   No testing is being done on any Python version prior to 3.11 and no changes
    or issue reports will be accepted for these versions.

*   The [lava operator](#lava-iam-components) IAM role now has access to the
    realm *user* KMS key to enable the role to be used to dispatch jobs.
    (Credit AN)

*   The [slack](#connector-type-slack) connector can now read the Slack webhook
    URL from an AWS SSM parameter as an optional alternative to storing it as
    a literal in the connection specification.

*   An SQS queue has been introduced between the `lava-<REALM>-dispatch` SNS
    topic and the dispatch helper AWS Lambda function.
    See [The Dispatch Helper](#the-dispatch-helper) for more information.

*   The following changes have been made to the [email](#connector-type-email)
    connector:
    
    *   Reply-to addresses specified in the connection specification are now
        handled correctly.

    *   Email addresses can now be in full RFC 5322 format
         as well as bare email addresses (e.g. `J Smith <j.smith@example.com>`
        vs `j.smith@example.com`).

    *   `Date`, `Message-Id` and `User-Agent` headers are now explicitly added
        to email messages. The domain in the `Message-Id` can be controlled  
        with the [EMAIL_MSGID_DOMAIN](#configuration-for-the-email-connector)
        worker configuration parameter.

*   The [sqlite3](#connector-type-sqlite3) connector now disables use of any
    local init file (e.g. `~/.sqliterc`).

#### Version 8.2.0 ([Kīlauea](https://en.wikipedia.org/wiki/Kīlauea))

This version is functionally identical to v8.1, insofar as the main lava code
is concerned, hence the appellation has been retained. A number of changes have
been made to elements of packaging, deployment and documentation.

Changes are:

*   Added the [lava-new](#lava-new-utility) utility. This is the preferred way
    of creating a new [lava-job-framework](#the-lava-job-framework) project and
    replaces the old cookiecutter bundle approach. The latter is still available
    but is now deprecated.

*   Some slight reordering and updating of questions has been done when creating
    a new [lava-job-framework](#the-lava-job-framework) project.

*   A bunch of packaging stuff has been updated for the open source release.

*   The user guide has been converted to
    [mkdocs material](https://squidfunk.github.io/mkdocs-material/)
    and Sphinx has been replaced by
    [mkdocstrings](https://mkdocstrings.github.io)
    for API documentation. As a result, the other publication formats for the
    user guide (DOCX, EPUB etc.) have been discontinued.

*   A number of changes have been made to the management of the
    [lava docker images](#docker-images-for-lava), none of which impact image
    functionality. Probably. (Credit SYM)

    *   The lava docker images are now created without attestation manifests. If
        you don't know that means, you won't miss them. If you do know what that
        means, you may wonder why they were there in the first place. ¯\\_(ツ)_/¯

    *   Previous versions of lava used AWS ECR as a private registry for
        publishing images internally. This is still possible. The default
        registry for publication is now GitHub Container Registry (ghcr.io).

    *   The naming for publicly available lava docker images is:    
        &nbsp;&nbsp;&nbsp;&nbsp;`ghcr.io:jin-gizmo/lava/<PLATFORM>/<TYPE>`.    
        e.g:    
        &nbsp;&nbsp;&nbsp;&nbsp;`ghcr.io/jin-gizmo/lava/amzn2023/base`    

    *   Images published privately to AWS ECR retain the following format for
        compatibility with lava realm IAM structures:    
        &nbsp;&nbsp;&nbsp;&nbsp;`<ECR>:dist/lava/<PLATFORM>/<TYPE>`    
        e.g.    
        &nbsp;&nbsp;&nbsp;&nbsp;`123456789123.dkr.ecr.ap-southeast-2.amazonaws.com/dist/lava/amzn2023/base`    

    *   The [lava job framework](#the-lava-job-framework) defaults have been
        updated to reference the public images, by default. This change will not
        affect existing projects and can be altered on a per project basis, as
        needed.

    *   The Rocky Linux lava image (`rocky9`) has been discontinued. As if 
        anyone will notice. The build code has moved into a legacy area in the
        repo on the off-chance it is required but it is not maintained.

*   Lava has changed from [semantic versioning](https://semver.org) to
    [PEP 440](https://peps.python.org/pep-0440/) versioning. You would have to
    be doing something pretty unusual to notice the difference for main-line
    releases. The change was made to simplify working with PyPI. I promise lava
    will *never* have a version number like `1.0b2.post345.dev456`, although the
    techno-masochists among you will be aquiver with the new-found possibility.
    The semantic versioning support code has been left in (and repaired), just
    in case, but lava itself no longer uses it.

#### Version 8.1 ([Kīlauea](https://en.wikipedia.org/wiki/Kīlauea))

#### Version 8.0 ([Incahuasi](https://en.wikipedia.org/wiki/Incahuasi))

## Version 7

#### Version 7.1 ([Pichincha](https://en.wikipedia.org/wiki/https://en.wikipedia.org/wiki/Pichincha_(volcano)))

#### Version 7.0 ([Tronador](https://en.wikipedia.org/wiki/Tronador))

## Version 6

#### Version 6.3 ([Chimborazo](https://en.wikipedia.org/wiki/Chimborazo))

#### Version 6.2 ([Reventador](https://en.wikipedia.org/wiki/Reventador))

#### Version 6.1 ([Volcán Pinta](https://www.volcanodiscovery.com/fr/pinta.html))

#### Version 6.0 ([La Cumbre](https://en.wikipedia.org/wiki/La_Cumbre_(Galápagos_Islands)))

## Version 5

#### Version 5.1 ([Tungurahua](https://en.wikipedia.org/wiki/Tungurahua))

#### Version 5.0 ([Cotopaxi](https://en.wikipedia.org/wiki/Cotopaxi))

## Version 4

#### Version 4.3 ([Volcán Wolf)](https://en.wikipedia.org/wiki/Volcán_Wolf)

#### Version 4.2 ([Fernandina](https://en.wikipedia.org/wiki/Fernandina_Island))

#### Version 4.1 ([Sierra Negra](https://en.wikipedia.org/wiki/Sierra_Negra_(Galápagos)))
