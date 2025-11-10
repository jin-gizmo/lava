
## Usage Guidelines

A key goal of the framework is to facilitate the separation of environment
specific configuration details from the structure and logic of a lava based
solution. When developing lava solution components it is critical to properly
parameterise the various components to allow the same solution to be rapidly
migrated from one environment to another (e.g. dev to prod).

The following guidelines should be considered:

1.  Become familiar with basic [Jinja](https://jinja.palletsprojects.com/)
    syntax. Jinja is used extensively in lava and the job framework.

2.  Never hard-code any environment specific information into source code.
    These details should be properly parameterised and values provided by the
    environment configuration file at build time. Typical environment specific
    information includes S3 bucket names, database identifiers, schema names,
    host names and addresses etc.
    
3.  Complete solution design, implementation and testing in a single development
    environment. Once done, the configuration file can be cloned for other
    environments and the parameters adjusted appropriately. Building for these
    other environments is then a quick and easy process.
