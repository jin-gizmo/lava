
## Connector type: slack

The **slack** connector uses
[Slack webhooks](https://api.slack.com/messaging/webhooks) to send
messages to Slack channels. The target Slack workspace and channel are specified
in Slack itself when the webhook is created.

|Field|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|colour|Style|No|Default colour for the sidebar for Slack messages sent using `attachment` style. This can be any hex colour code or one of the Slack special values `good`, `warning` or `danger`. If not specified a default value is used.|
|conn\_id|String|Yes|Connection identifier.|
|description|String|No|Description.|
|enabled|Boolean|Yes|Whether or not the connection is enabled.|
|from|String|No|An arbitrary source identifier for display in Slack messages. If not specified, a default value is constructed when required.|
|preamble|String|No|Default preamble at the start of Slack messages. Useful values include things such as `<!here>` and `<!channel>` which will cause Slack to insert `@here` and `@channel` alert tags respectively. If not specified, no preamble is used.|
|style|String|No|Display style for Slack messages. Options are `block` (default), `attachment` and `plain`. The first two use the corresponding block or attachment message construction mechanism provided by Slack to make messages more presentable.|
|type|String|Yes|`slack`.|
|webhook_url|String|Yes|The [webhook URL](https://api.slack.com/messaging/webhooks) provided by Slack for sending messages.|

### Using the Slack Connector

The **slack** connector provides two distinct interfaces:

1.  A [native Python interface](#python-interface-for-slack-connectors)

2.  A [command line interface](#executable-interface-for-slack-connectors).

#### Python Interface for Slack Connectors

Python scripts can directly access the underlying Python interface of a **slack**
connector. In this case, the connector returns a `lava.lib.slack.Slack`
object as described in the lava API documentation.

As an example, consider an [exe](#job-type-exe) job specification
that looks something like this:

```json
{
    "job_id": "...",
    "parameters": {
        "connections": {
            "slack": "slack-connection-id"
        }
    },
    "payload": "my-payload.py ..."
}
```

A Python program can use the **slack** connector like this:


```python
import os
from lava.connection import get_slack_connection

# If running as a lava exe/pkg/docker, get some info provided by lava in the
# environment. Assume our connector is labeled `slack` in the job spec.
realm = os.environ['LAVA_REALM']
conn_id = os.environ['LAVA_CONNID_SLACK']

# Get a slack connection 
slacker = get_slack_connection(conn_id, realm)

# Send a formatted message
slacker.send(
    subject='Oh no',
    message='Your oscillation overthruster has malfunctioned',
    style='attachment',  # Overrides value in connection spec.
    colour='#ff0000'  # Nice bright red. Overrides value in connection spec.
)

```

#### Executable Interface for Slack Connectors

When used with [exe](#job-type-exe),
[pkg](#job-type-pkg) and
[docker](#job-type-docker) job types (e.g. shell scripts), the
connection is implemented by the `lava-slack` command.

When used as a connection script within a lava job, the `-r REALM` and
`-c CONN_ID` arguments don't need to be provided by the job as these are
provided by lava in the connection script.

Also, values for the `---bar-colour`, `--from`, ` --preamble` and `--style`
options will be supplied from the connection specification where possible.
These values can be overridden by providing the appropriate options to then
connection script.

```bare
usage: lava-slack [-h] [--profile PROFILE] [-v] -c CONN_ID [-r REALM]
                  [--bar-colour COLOUR] [--from NAME] [--preamble PREAMBLE]
                  [-s SUBJECT] [--style {block,plain,attachment}]
                  [--no-colour] [-l LEVEL] [--log LOG] [--tag TAG]
                  [FILENAME]

Send Slack messages using lava slack connections.

optional arguments:
  -h, --help            show this help message and exit
  --profile PROFILE     As for AWS CLI.
  -v, --version         show program's version number and exit

lava arguments:
  -c CONN_ID, --conn-id CONN_ID
                        Lava connection ID. Required.
  -r REALM, --realm REALM
                        Lava realm name. If not specified, the environment
                        variable LAVA_REALM must be set.

slack arguments:
  --bar-colour COLOUR   Colour for the sidebar for messages sent using
                        attachment style. This can be any hex colour code or
                        one of the Slack special values good, warning or
                        danger.
  --from NAME           Message sender. If not specified, the value specified
                        in the connection specification, if any, will be used.
  --preamble PREAMBLE   An optional preamble at the start of the message.
                        Useful values include things such as <!here> and
                        <!channel> which will cause Slack to insert @here and
                        @channel alert tags respectively.
  -s SUBJECT, --subject SUBJECT
                        Message subject.
  --style {block,plain,attachment}
                        Slack message style. Must be one of attachment, block,
                        plain. If not specified, any value specified in the
                        connection specification will be used or block as a
                        last resort.

message source arguments:
  FILENAME              Name of file containing the message body. If not
                        specified or "-", the body will be read from stdin.
                        Only the first 3000 bytes are read.

logging arguments:
  --no-colour, --no-color
                        Don't use colour in information messages.
  -l LEVEL, --level LEVEL
                        Print messages of a given severity level or above. The
                        standard logging level names are available but debug,
                        info, warning and error are most useful. The default
                        is info.
  --log LOG             Log to the specified target. This can be either a file
                        name or a syslog facility with an @ prefix (e.g.
                        @local0).
  --tag TAG             Tag log entries with the specified value. The default
                        is lava-slack.
```

As an example, consider an [exe](#job-type-exe) job specification
that looks something like this:

```json
{
    "job_id": "...",
    "parameters": {
        "connections": {
            "slack": "slack-connection-id"
        }
    },
    "payload": "my-payload.sh ..."
}
```

Note the `slack` connection. This will provide the job with an environment
variable `LAVA_CONN_SLACK` which points to the executable handling the
connection.

If the job payload is a shell script, the connector would be invoked thus:

```bash
# Send a Slack message
$LAVA_CONN_SLACK --subject "Oh no" <<!
    Dear Buckaroo,
 
    Your oscillation overthruster has malfunctioned.

    -- John Bigbooté
!
```
