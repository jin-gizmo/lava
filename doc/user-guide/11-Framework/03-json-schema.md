
## Working with the JSON Schemas

!!! note
    New in v8.3.0 (Mauna Loa).

The lava job framework leverages the [hosted JSON schemas](#lava-json-schemas)
to:

*   Provide syntax support when editing in IDEs that support such things (e.g.
    JetBrains suite and VS Code); and

*   Perform pre-install validation of built artefacts.

The default setup will always use the latest versions of the schemas. While it
is possible to reference a specific version of the schemas, this should not be
done lightly. The schemas are quite stable and it is fiddly to use anything
other than the latest version.

### Using Lava JSON Schemas for IDE Support { data-toc-label="IDE Support" }

For editing support, the YAML source files must include a `$schema:` attribute
that references the **YAML** version of the relevant schema. The provided [lava
job framework samples](#lava-job-framework-samples) show the appropriate entry.
The `$schema` attribute is not deployed to DynamoDB.

If you have an existing lava job framework project without `$schema:`
attributes, these can be quickly added using `make set-schema` (framework
version >= v8.3.0).

The `$schema` entries are there purely for the IDE. Schema validation by the
`lava-schema` utility will completely ignore them and use its own logic for
schema selection. This is not a problem unless you are doing something odd.

There are legitimate reasons why a YAML source file will sometimes not
completely match the schema, principally because it has not yet been through the
[Jinja rendering](#jinja-rendering-of-dynamodb-items). Even so, using the
schemas is helpful at this stage.

!!! note
    The JSON schema support in JetBrains PyCharm is, occasionally, idiosyncratic.
    Don't fret. It's still useful. Do make sure to use the YAML schemas in YAML
    source files.

#### Using Lava JSON Schemas for Validation { data-toc-label="Schema Validation" }

The lava job framework will perform pre-install validation of the built
artefacts (i.e. post Jinja rendering) using a bundled version of the
[lava-schema](#lava-schema-utility) utility.

If validation fails, no deployment.

!!! note
    It is important to take any errors at this point seriously.
    Yes, of course there is a way to bypass validation. Don't go looking for it.

One cause of schema errors at this point is omission of essential elements (e.g.
job parameters) with the expectation that the [lava dispatch
process](#the-lava-dispatch-process) will add them at run-time. It is
**important** to include placeholders for these items, both for schema
validation purposes and as a form of documentation.

To run the pre-install schema validation manually:

```bash
# Note we need to do a build first
make dist pre-install env=<ENV>
```
