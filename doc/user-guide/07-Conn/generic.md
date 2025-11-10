
##  Connector type: generic

The **generic** connector provides a general purpose mechanism to group a set of
associated attributes together and have them made available to lava jobs at
run-time. Lava doesn't actually *connect* to any external resources other than
to obtain attribute values.

|Field|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|conn\_id|String|Yes|Connection identifier.|
|description|String|No|Description.|
|enabled|Boolean|Yes|Whether or not the connection is enabled.|
|attributes|Map[String,\*]|Yes|A map comprising the attributes for the connector. The keys are the attribute names and the values are either simple scalars or another map specifying how to obtain the value. See [below](#specifying-generic-connector-attribute-values) for more information.|
|type|String|Yes|`generic`.|

### Specifying Generic Connector Attribute Values { data-toc-label="Specifying Attribute Vales" }

The `attributes` field of the **generic** connector specifies the names of the
connector attributes and how the attribute values are obtained. The following
variants are supported.

#### Simple Scalar Attributes

Simple scalar attributes are specified thus:

```json
{
  "attributes": {
    "name": "value"
  }
}
```

In addition to string values, integer and float values are also supported.

#### Local Parameters

This is an alternative syntax to the simple scalar attribute syntax described
above.

```json
{
  "attributes": {
    "name": {
      "type": "local",
      "value": "value"
    }
  }
}
```

#### SSM Parameters

Values from SSM parameters are specified thus:

```json
{
  "attributes": {
    "name": {
      "type": "ssm",
      "parameter": "SSM parameter name"
    }
  }
}
```

Lava will obtain the value from the SSM parameter store, decrypting as required.

### Example Generic Connector Specification { data-toc-label="Example" }

```json
{
  "conn_id": "widget-conn-id",
  "description": "Sample generic connector",
  "enabled": true,
  "type": "generic",
  "attributes": {
    "a": "a string",
    "b": {
      "type": "local",
      "value": 30
    },
    "c": {
      "type": "ssm",
      "parameter": "/lava/<REALM>/my_var"
    }
  }
}
```

### Using the Generic Connector

The **generic** connector provides two distinct interfaces:

1.  A [native Python interface](#python-interface-for-generic-connectors)

2.  A [command line interface](#executable-interface-for-generic-connectors).

#### Python Interface for Generic Connectors

Python scripts can directly access the underlying Python interface of a **generic**
connector. In this case, the connector returns a dictionary of resolved attribute
values.

As an example, consider an [exe](#job-type-exe) job specification
that looks something like this:

```json
{
    "job_id": "...",
    "parameters": {
        "connections": {
            "widget": "widget-connection-id"
        }
    },
    "payload": "my-payload.py ..."
}
```

A Python program can use the **generic** connector like this:

```python
import os
from lava.connection import get_generic_connection

# If running as a lava exe/pkg/docker, get some info provided by lava in the
# environment. Assume our connector is labeled `widget` in the job spec.
realm = os.environ['LAVA_REALM']
conn_id = os.environ['LAVA_CONNID_WIDGET']

attributes = get_generic_connection(conn_id, realm)
```

The `attributes` dictionary would then look like:

```python
{
    'a': 'a string',
    'b': 30,
    'c': 'Value of SSM parameter /lava/<REALM>/my_var'
}
```

#### Executable Interface for Generic Connectors

When used with [exe](#job-type-exe),
[pkg](#job-type-pkg) and
[docker](#job-type-docker) job types (e.g. shell scripts), the
connection is implemented by a simple script that can be used to obtain the
value of individual attributes.

As an example, consider an [exe](#job-type-exe) job specification
that looks something like this:

```json
{
  "job_id": "...",
  "parameters": {
    "connections": {
      "widget": "widget-connection-id"
    }
  },
  "payload": "my-payload.sh ..."
}
```

Note the `widget` connection. This will provide the job with an environment
variable `LAVA_CONN_WIDGET` which points to the executable handling the
connection.

If the job payload is a shell script, the connector would be invoked thus:

```bash
# Get the values of the attributes
ATTR_A=$($LAVA_CONN_WIDGET a)
ATTR_B=$($LAVA_CONN_WIDGET b)
ATTR_C=$($LAVA_CONN_WIDGET c)
```
