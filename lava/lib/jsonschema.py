"""
JSONschema utilities.

As of v7.1.0 (Pichincha), a full (well... pretty full) JSON schema is provided
for the DyanmoDB entries. Over time, lava will be progressively more aggressive
in validating against these.

!!! question "Why JSONschema instead of Cerberus, Pydantic ...?"
    I don't know. Seemed like a good idea at the time and I can't be bothered
    changing it now.

"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from glob import glob

import jsonschema
import yaml
from dateutil.parser import isoparse

JSON_SCHEMA = 'https://json-schema.org/draft/2020-12/schema'
FORMAT_CHECKER = jsonschema.draft202012_format_checker
SCHEMA_DIR = os.path.join(os.path.dirname(__file__), 'schema')


@dataclass(frozen=True)
class LavaSpecInfo:
    """Lava DynamoDB table names and corresponding hash key."""

    table: str
    key: str


LAVA_SCHEMA_INFO = {
    'job': LavaSpecInfo('jobs', 'job_id'),  # noqa
    's3trigger': LavaSpecInfo('s3triggers', 'trigger_id'),  # noqa
    'connection': LavaSpecInfo('connections', 'conn_id'),  # noqa
}


# ------------------------------------------------------------------------------
@FORMAT_CHECKER.checks('iso8601', raises=(ValueError,))
def is_iso8601(value: str) -> bool:
    """
    Check if a string is ISO 8601.

    This is a bit more tolerant than the built in `date-time` format check in
    that it accepts values without a timezone.

    """

    isoparse(value)
    return True


# ------------------------------------------------------------------------------
def jsonschema_resolver_store_from_directory(
    dirname: str, fmt: str = 'YAML', validate=True
) -> dict[str, dict]:
    """
    Create a jsonschema resolver store with contents of a directory pre-loaded.

    The keys in the store are the '$id' field from the file if present, otherwise
    the relative filename with the suffix removed and path separators converted
    to dots. So `a.b.c.yaml` and `a/b/c.yaml` both become `a.b.c`.

    :param dirname:     Directory name.
    :param fmt:         Either YAML or JSON. Schema files must end with `.yaml`
                        or `.json` respectively.
    :param validate:    If True, validate schemas as they are loaded.
    :return:            A schema resolver store which is basically a mapping
                        from a $ref value to the schema contents.
    """

    store = {}

    if fmt == 'YAML':
        loader, glob_pattern = yaml.safe_load, '*.yaml'
    elif fmt == 'JSON':
        loader, glob_pattern = json.load, '*.json'
    else:
        raise ValueError(f'Unkown format: {fmt}')

    for f in glob(os.path.join(dirname, '**', glob_pattern), recursive=True):
        with open(f) as fp:
            schema = loader(fp)

        if validate:
            try:
                jsonschema.validators.validator_for(schema).check_schema(schema)
            except jsonschema.SchemaError as e:
                raise Exception(f'{f}: {e}')

        schema_id = schema.get(
            '$id', os.path.splitext(os.path.relpath(f, dirname))[0].replace(os.path.sep, '.')
        )

        store[schema_id] = schema

    return store
