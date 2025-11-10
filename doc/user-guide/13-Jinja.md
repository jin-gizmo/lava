
# Jinja Rendering in Lava

Lava uses [Jinja](http://jinja.pocoo.org/) extensively to provide flexibility
in the preparation of job payloads, parameters and
[post-job actions](#job-actions).

The full range of Jinja syntax is available, including attribute value
substitutions using `{{ ... }}` delimiters and control structures (loops,
conditionals etc.) using `{% ... %}` syntax.

!!! info
    Note that the [lava job framework](#the-lava-job-framework)
    deliberately uses `<{ ...}>`and `<% ... %>` delimiters to differentiate
    between build-time rendering done in the framework and run-time rendering
    performed by the lava worker.

The attributes made available to the renderer vary by job and action type.
Typically they include elements such as:

*   realm specification details

*   [augmented job specification](#the-augmented-job-specification)
    details

*   job run details

*   job [globals](#globals), which includes user defined globals and
    [globals owned and provided by lava](#globals-owned-by-lava)

*   [state item](#the-lava-state-manager) values.


Attributes provided to the renderer are typically one of the following types:

*   Scalar values (strings, integers etc)

*   [Structured objects](#working-with-structured-attributes)

*   [DateTime values](#working-with-datetime-attributes)

*   [Utility functions](#jinja-utility-functions) provided for
    convenience.

Refer to specific job and action types for details.

## The Augmented Job Specification

The job specification passed to the Jinja renderer for jobs and actions
has the same contents as the relevant item from the
[jobs](#the-jobs-table) table with the addition of the
following elements:

|Name|Type|Description|
|-|-|-------------------------------------------------------------|
|realm|str|The realm name.|
|run_id|str|The run ID.|
|state|dict[str,\*]|The state map from the [job](#the-jobs-table) specification, updated to replace the default values from the map with any current values obtainable from the [state](#the-state-table) table.|
|ts_dispatch|datetime|The timezone aware datetime when the job was dispatched.|
|ts_start|datetime|The timezone aware local datetime when the job started.|
|ts_ustart|datetime|The timezone aware UTC datetime when the job started.|

## Working with Structured Attributes { data-toc-label="Structured Attributes" }

Some of the attributes passed to the Jinja renderer are structured objects.

For example, the `realm` attribute is the DynamoDB map object from the
[realms](#the-realms-table) table for the realm. This is
converted to a Python dictionary and passed in that form to the Jinja renderer.
Elements of this object can be referenced using standard Jinja object
references.  For example, the realm name can be injected as either
`{{ realm.realm }}` or `{{ realm["realm"] }}`.

## Working with DateTime Attributes { data-toc-label="DateTime Attributes" }

Some of the attributes passed to the Jinja renderer are DateTime attributes.
These include the `start` and `ustart` attributes that capture the job start
time in local and UTC time respectively.

Within Jinja, these become standard Python
[datetime.datetime](https://docs.python.org/3/library/datetime.html) objects.
Jinja thus provides access to all the methods associated with a Python
datetime. The
[strptime()](https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior)
method is particularly useful. For example:

```jinja
{# Get the job start date in local time #}
{{ start.strptime('%Y-%m-%d') }}

{# Get the job start time in UTC as an ISOO 8601 format timestamp #}
{{ ustart.isoformat() }}
```

It is even possible to do some elementary date calculations, although this can
be accomplished more easily since lava version 4.3.0 (Volcán Wolf) using the
provided [utility functions](#jinja-utility-functions).

```jinja
{# Calculate yesterday's date #}
{{ (start.fromtimestamp(start.timestamp()-86400)).date() }}
```

## Jinja Utility Functions

Lava also provides a number of utilities to the Jinja renderer as
Python runnable objects in the `utils` attribute.

#### date

This is the standard Python
[datetime.date](https://docs.python.org/3/library/datetime.html#datetime.date)
class.

```jinja
{# The epoch #}
{{ utils.date(year=1970, month=1, day=1) }}

{# What day of the week is next year's ANZAC day? #}
{{ utils.date(year=ustart.year + 1, month=4, day=25).strftime('%A') }}

```

#### datetime

This is the standard Python
[datetime.datetime](https://docs.python.org/3/library/datetime.html#datetime.datetime)
class.

```jinja
{# Next new year's day #}
{{ utils.datetime(year=ustart.year + 1, month=1, day=1) }}

{# What day of the week is that? #}
{{ utils.datetime(year=ustart.year + 1, month=1, day=1).strftime('%A') }}

```

#### dateutil

This is the [dateutil](https://dateutil.readthedocs.io/en/stable/index.html)
Python module.

```jinja
{# Get the date 6 months from now #}
{{ ustart + utils.dateutil.relativedelta.relativedelta(months=6) }}
```

If the long module path gets too painful ...

```jinja
{% set relativedelta = utils.dateutil.relativedelta.relativedelta %}
{{ ustart + relativedelta(months=6) }}
```

#### parsedate

This is the
[dateutil.parser](https://dateutil.readthedocs.io/en/stable/parser.html#dateutil.parser)
module. It is useful for parsing strings into dates.

```jinja
{# Convert a string back to a datetime #}
{{ utils.parsedate.isoparse('2020-02-11T09:30:00+11:00') }}
```

!!! note
    This is a legacy feature but is still supported. The
    alternative is `utils.dateutil.parser`.

#### path

This is the standard Python [os.path](https://docs.python.org/3/library/os.path.html)
module.

```jinja
{# "s3://bucket.xyzzy.com/an/s3/key" --> "key" #}
{{ utils.path.basename('s3://bucket.xyzzy.com/an/s3/key') }}

{# Get the last component of the lava temp bucket prefix #}
{{ utils.path.basename(realm.s3_temp) }}
```

#### re

This is the standard Python [re](https://docs.python.org/3/library/re.html)
(regex) module. It is useful for extracting selected components of other render
variables.


```jinja
{# "s3://bucket.xyzzy.com/an/s3/key" --> "bucket" #}
{{ utils.re.search('s3://([^.]*)', 's3://bucket.xyzzy.com/an/s3/key)'.group(1) }}
```

#### s3bucket

Extract the S3 bucket name component from a string.

```jinja
{# "s3://bucket.xyzzy.com/an/s3/key" --> "bucket.xyzzy.com" #}
{{ utils.s3bucket('s3://bucket.xyzzy.com/an/s3/key') }}

{# Get the lava temp bucket name #}
{{ utils.s3bucket(realm.s3_temp) }}
```

#### s3key

Extract the S3 key name component from a string.


```jinja
{# "s3://bucket.xyzzy.com/an/s3/key" --> "an/s3/key" #}
{{ utils.s3key('s3://bucket.xyzzy.com/an/s3/key') }}

{# Get the lava temp bucket prefix #}
{{ utils.s3key(realm.s3_temp) }}
```

#### time

This is the standard Python
[datetime.time](https://docs.python.org/3/library/datetime.html#datetime.time)
class.

#### timedelta

This is the standard Python
[datetime.timedelta](https://docs.python.org/3/library/datetime.html#datetime.timedelta)
class.

```jinja
{# Calculate yesterday's date #}
{{ (start - utils.timedelta(days=1)).date() }}

```

#### uuid

Generate a random UUID.

```jinja
{# Generate a random S3 object name #}
s3://bucket/some/prefix/{{ utils.uuid() }}.csv
```
