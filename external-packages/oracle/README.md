# Oracle ZIP install bundles

This directory contains the Oracle client install bundles. These are required
when building the lava docker images and the lava AMI. 

These components are required for both ARM and x86:

*   SQL*Plus
*   Oracle Instant Client Basic Light (or Basic). Unless you need the extra
    languages, use the "Light" version (English language only).

**DO NOT** populate this directory manually. There is a particular structure
required by the build processes (which becomes obvious once you have an initial
set of downloads). To download / update the required zip code bundles, do the
following from the top of the repo:

```bash
make oracle
```

Every now and then it's a good idea to clean out the old versions.
