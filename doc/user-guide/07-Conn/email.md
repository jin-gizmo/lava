
##  Connector type: email

The **email** connector provides a generic interface for an email sending
subsystem. It is implemented by one or more actual email handlers. The email
subsystem type is selected by the `subtype` field in the connection
specification. Each subtype may have extra field requirements of its own.

Currently supported email handler subtypes are:

*   `ses`: AWS Simple Email Service (SES)

*   `smtp`: SMTP, including optional TLS support.

|Field|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|conn\_id|String|Yes|Connection identifier.|
|description|String|No|Description.|
|enabled|Boolean|Yes|Whether or not the connection is enabled.|
|from|String|No|The email address that is sending the email. While this is not a mandatory field in the connector, there must be a value available at the time an email is sent, either from the job itself, the connection specification or an email handler specific mechanism. It is strongly recommended to include a default value in the connection specification.|
|reply\_to|String _or_ List[String]|No|The default reply-to email address(es) for messages.|
|subtype|String|No|Specifies the underlying email handler. If not specified, `ses` is assumed, in which case the field requirements for this subtype must be met.|
|type|String|Yes|`email`.|

### Subtype: ses

The `ses` subtype uses AWS Simple Email Service to send email.

The following fields are specific to the `ses` subtype.

|Field|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|configuration\_set|String|No|Use the specified SES Configuration Set when sending an email. If not specified, the value specified by the [SES_CONFIGURATION_SET](#general-configuration-parameters) realm configuration parameter is used.|
|from|String|No|The email address that is sending the email. This email address must be either individually verified with Amazon SES, or from a domain that has been verified with Amazon SES. If not specified, the value specified by the [SES_FROM](#general-configuration-parameters) realm configuration parameter is used. A value must be specified by one of these mechanisms.|
|region|String|No|The AWS region name for the SES service. If not specified, the value specified by the [SES_REGION](#general-configuration-parameters) realm configuration parameter is used, which itself defaults to `us-east-1`.|
|subtype|String|No|Either `ses` or missing.|

### Subtype: smtp

The `smtp` subtype uses standard SMTP to send email. SMTP over TLS is also
supported.

The following fields are specific to the `smtp` subtype.

|Field|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|host|String|Yes|The SMTP server host DNS name or IP address.|
|password|String|Sometimes|The name of an encrypted SSM parameter containing the SMTP server password. For a given `<REALM>`, the SSM parameter name must be of the form `/lava/<REALM>/...` and the value must be a **secure string** encrypted using the `lava-<REALM>-sys` KMS key. This field is required if the `host` field is specified.|
|port|Number|No|The SMTP port number. If not specified, the default is 25 without TLS and 465 with TLS. Note that Gmail requires TLS on port 587.|
|subtype|String|Yes|`smtp`|
|tls|Boolean|No|If `true`, use SMTP over TLS. Default is `false`.|
|user|String|No|SMTP server user name. If specified, the `password` field must also be specified. If not specified, the connection will be unauthenticated.|

### Using the Email Connector

The `email` connector provides two distinct interfaces:

1.  A [native Python interface](#python-interface-for-email-connectors)

2.  A [command line interface](#executable-interface-for-email-connectors).


#### Python Interface for Email Connectors

Python scripts can directly access the underlying Python interface of an email
connector. In this case, the connector returns a `lava.lib.email.Emailer`
object as described in the lava API documentation.

As an example, consider an [exe](#job-type-exe) job specification
that looks something like this:

```json
{
    "job_id": "...",
    "parameters": {
        "connections": {
            "email": "email-connection-id"
        }
    },
    "payload": "my-payload.py ..."
}
```

A Python program can use the email connector like this:


```python
import os
from lava.connection import get_email_connection

# If running as a lava exe/pkg/docker, get some info provided by lava in the
# environment. Assume our connector is labeled `email` in the job spec.
realm = os.environ['LAVA_REALM']
conn_id = os.environ['LAVA_CONNID_EMAIL']

# We can use the email connection as a context manager
with get_email_connection(conn_id, realm) as emailer:
    emailer.send(
        subject='Oh no',
        message='Your oscillation overthruster has malfunctioned',
        to='Buckaroo.Banzai@dimension8.com',
        cc=[
            'Professor.Hikita@dimension8.com',
            'Sidney Zweibel@dimension8.com'
        ]
    )

```

#### Executable Interface for Email Connectors

When used with [exe](#job-type-exe),
[pkg](#job-type-pkg) and
[docker](#job-type-docker) job types (e.g. shell scripts), the
connection is implemented by the `lava-email` command.

When used as a connection script within a lava job, the `-r REALM` and
`-c CONN_ID` arguments don't need to be provided by the job as these are
provided by lava in the connection script.

Also, values for the `--from` and `--reply-to` options will be provided by lava
if it has values available from the connection specification or other
configuration data. These values can be overridden by providing the appropriate
options to then connection script.

??? "lava-email Usage"

    ```bare
    usage: lava-email [-h] [--profile PROFILE] [-v] -c CONN_ID [-r REALM]
                      [--bcc EMAIL] [--cc EMAIL] [--from EMAIL] [--reply-to EMAIL]
                      [--to EMAIL] -s SUBJECT [--html FILENAME] [--text FILENAME]
                      [--no-colour] [-l LEVEL] [--log LOG] [--tag TAG]
                      [FILENAME]

    Send email using lava email connections.

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

    email arguments:
      --bcc EMAIL           Recipients to place on the Bcc: line of the message.
                            Can be used multiple times.
      --cc EMAIL            Recipients to place on the Cc: line of the message.
                            Can be used multiple times.
      --from EMAIL          Message sender. If not specified, a value must be
                            available in either the connection specification or
                            the realm specification.
      --reply-to EMAIL      Reply-to address of the message.Can be used multiple
                            times.
      --to EMAIL            Recipients to place on the To: line of the message.Can
                            be used multiple times.
      -s SUBJECT, --subject SUBJECT
                            Message subject. Required.

    message source arguments:
      At most one of the following arguments is permitted.

      --html FILENAME       This is a legacy argument for backward compatibility.
      --text FILENAME       This is a legacy argument for backward compatibility.
      FILENAME              Name of file containing the message body. If not
                            specified or "-", the body will be read from stdin. An
                            attempt is made to determine if the message is HTML and
                            send it accordingly. Only the first 2MB is read.

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
                            is lava-email.
    ```

As an example, consider an [exe](#job-type-exe) job specification
that looks something like this:

```json
{
    "job_id": "...",
    "parameters": {
        "connections": {
            "email": "email-connection-id"
        }
    },
    "payload": "my-payload.sh ..."
}
```

Note the `email` connection. This will provide the job with an environment
variable `LAVA_CONN_EMAIL` which points to the executable handling the
connection.

If the job payload is a shell script, the connector would be invoked thus:

```bash
# Send an email with a text message body.
$LAVA_CONN_EMAIL --to Buckaroo.Banzai@dimension8.com --subject "Oh no" <<!
    Dear Buckaroo,
 
    Your oscillation overthruster has malfunctioned.

    -- John Bigbooté
!

# But wait -- we can do HTML as well
$LAVA_CONN_EMAIL --to Buckaroo.Banzai@dimension8.com --subject "Oh no" <<!
<HTML>
    <BODY>
        <P>Dear Buckaroo,</P>
        <P>Your oscillation overthruster has malfunctioned</P>
        <P>-- John Bigbooté</P>
    </BODY>
</HTML>
!

```
