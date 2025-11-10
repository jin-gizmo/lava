
## The Lava State API

The lava state API provides for the posting and retrieval of state items.

The code to post a state item would look like this:

```python
import os
from lava.lib.state import LavaStateItem

realm = os.environ['LAVA_REALM']

value1 = "Hello world"
# .. or maybe ...
value2 = {
    "volcano_name": "Tronador",
    "elevation": 3491,
    "active": False
}

# Create our item. This is a local operation so far.
my_state_item = LavaStateItem.new('json', 'my_state_id', realm, value1, ttl='2d')

# Changed my mind
my_state_item.value = value2

# Post to DynamoDB
my_state_item.put()
```

Secure state items are KMS encrypted for storage and automatically decrypted on
loading. An additional parameter, `kms_key`, specifies the KMS key to use, either
as a KMS key ARN or a key alias in the form `alias/key-id`. This defaults to the
`sys` key for the lava realm.

!!! info
    Note that the use of KMS encryption imposes a maximum size limit of 4096 bytes
    on the JSON encoded state item value.

```python
import os
from lava.lib.state import LavaStateItem

realm = os.environ['LAVA_REALM']
value = 'Big Secret'

# Create a secure item with the default key.
my_state_item = LavaStateItem.new('secure', 'my_state_id', realm, value)

# or
my_state_item = LavaStateItem.new(
    'secure', 'my_state_id', realm, value, kms_key='alias/my-key'
)
```

To retrieve a state item:

```python
import os
from lava.lib.state import LavaStateItem

realm = os.environ['LAVA_REALM']

value = LavaStateItem.get('my_state_id', realm).value
```

The lava state manager handles all the encoding / decoding processes and the
interaction with DynamoDB.
