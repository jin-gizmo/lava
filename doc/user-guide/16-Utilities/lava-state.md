
## Lava State Utility { data-toc-label="lava-state" }

The lava state utility provides a CLI to the
[lava state manager](#the-lava-state-manager).

??? "Usage"

    ```bare
    usage: lava-state [-h] [--profile PROFILE] [-r REALM] [-v] [--no-colour]
                      [-l LEVEL] [--log LOG] [--tag TAG]
                      {put,get} ...

    Manipulate lava state entries.

    positional arguments:
      {put,get}
        put                 Add / replace a state entry.
        get                 Get a state entry.

    optional arguments:
      -h, --help            show this help message and exit
      --profile PROFILE     As for AWS CLI.
      -r REALM, --realm REALM
                            Lava realm name. If not specified, the environment
                            variable LAVA_REALM must be set.
      -v, --version         show program's version number and exit

    logging arguments:
      --no-colour, --no-color
                            Don't use colour in information messages.
      -l LEVEL, --level LEVEL
                            Print messages of a given severity level or above. The
                            standard logging level names are available but debug,
                            info, warning and error are most useful. The Default
                            is info.
      --log LOG             Log to the specified target. This can be either a file
                            name or a syslog facility with an @ prefix (e.g.
                            @local0).
      --tag TAG             Tag log entries with the specified value. The default
                            is lava-state.
    ```

### Creating a Lava State Item

State items are created with the `put` sub-command.

!!! info
    Do not create state items with a `state_id` starting with `lava`.
    This prefix is reserved.

??? "Usage: lava-state put"

    ```bare
    usage: lava-state put [-h] [-p KEY=VALUE | -v VALUE] [--kms-key KMS_KEY]
                          [--publisher PUBLISHER] [--ttl DURATION]
                          [--type STATE_TYPE]
                          state_id

    positional arguments:
      state_id              State ID.

    optional arguments:
      -h, --help            show this help message and exit
      -p KEY=VALUE, --param KEY=VALUE
                            Add the specified key/value pair to the state item.
                            Can be repeated to set multiple key/value pairs.
      -v VALUE, --value VALUE
                            Set the value to the specified string.
      --kms-key KMS_KEY     The "secure" state item type supports KMS encryption
                            of the value. This argument specifies the KMS key to
                            use, either as a KMS key ARN or a key alias in the
                            form "alias/key-id". Defaults to the "sys" key for the
                            lava realm. Ignored for other state item types.
      --publisher PUBLISHER
                            Set the state item publisher to the specified value.
                            Default is the contents of the LAVA_JOB_ID environment
                            variable, if set, or else "lava-state CLI".
      --ttl DURATION        Time to live as a duration (e.g. 10m, 2h, 1d).
      --type STATE_TYPE     State item type. Options are json, raw, secure.
                            Default is json.
    ```

### Retrieving a Lava State Item

State items are retrieved with the `get` sub-command.

??? "Usage: lava-state get"

    ```bare
    usage: lava-state get [-h] [-i] state_id [template]

    positional arguments:
      state_id              State ID.
      template              An optional Jinja2 template that will be rendered with
                            the retrieved value as the "state" and "s" parameters.
                            e.g if set to "{{ state }}" (the default) the value is
                            printed as is.

    optional arguments:
      -h, --help            show this help message and exit
      -i, --ignore-missing  Ignore errors for missing state items and return an
                            empty string. By default, attempting to get a non-
                            existent state item is an error.
    ```
