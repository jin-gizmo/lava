
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

* Support for Python 3.9 will end. Seriously, just stop using it.

## Version 8

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
    functionality. Probably.

    *   The lava docker images are now created without attestation manifests. If
        you don't know that means, you won't miss them. If you do know what that
        means, you may wonder why they were there in the first place. ¯\\_(ツ)_/¯

    *   Previous versions of lava used AWS ECR as a private registry for
        publishing images internally. This is still possible. The default
        registry for publication is now GitHub Container Registry (ghcr.io).

    *   The naming for publicly available lava docker images is:    
            `ghcr.io:jin-gizmo/lava/<PLATFORM>/<TYPE>`.    
        e.g:    
            `ghcr.io/jin-gizmo/lava/amzn2023/base`    

    *   Images published privately to AWS ECR retain the following format for
        compatibility with lava realm IAM structures:    
            `<ECR>:dist/lava/<PLATFORM>/<TYPE>`    
        e.g.    
            `123456789123.dkr.ecr.ap-southeast-2.amazonaws.com/dist/lava/amzn2023/base`    

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
