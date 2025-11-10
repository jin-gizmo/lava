
## Connector type: ses

!!! warning
    This is a legacy implementation. It is now deprecated and will be removed in
    a future release. Use the [email](#connector-type-email)
    connector instead.

The **ses** connector provides access to the AWS Simple Email Service (SES).

If can be used only with [exe](#job-type-exe) and [pkg](#job-type-pkg) jobs. It provides an environment variable
pointing to a script that will run the AWS CLI with appropriate
parameters to access the SES service.

|Field|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|conn\_id|String|Yes|Connection identifier.|
|description|String|No|Description.|
|enabled|Boolean|Yes|Whether or not the connection is enabled.|
|from|String|No|The email address that is sending the email. This email address must be either individually verified with Amazon SES, or  from  a  domain that  has been verified with Amazon SES. If not specified, the value specified by the [SES_FROM](#general-configuration-parameters) realm configuration parameter is used. A value must be specified by one of these mechanisms.|
|region|String|No|The AWS region name for the SES service. If not specified, the value specified by the [SES_REGION](#general-configuration-parameters) realm configuration parameter is used, which itself defaults to `us-east-1`.|
|reply_to|String _or_ List[String]|No|The reply-to email address(es) for messages.|
|return_path|String|No|The email address that bounces and complaints will be  forwarded  to when feedback forwarding is enabled.|

In an [exe](#job-type-exe) or package
[pkg](#job-type-pkg) job, the job specification will look something
like this:

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
$LAVA_CONN_EMAIL --to fred@somewhere.com --subject "Hello Fred" --text msg.txt

# But wait -- we can do HTML as well
$LAVA_CONN_EMAIL --to fred@somewhere.com --subject "Hello Fred" --html msg.html

# Or read from stdin. The connector will look for <HTML> at start of message
# to determine if message is text or HTML.
$LAVA_CONN_EMAIL --to fred@somewhere.com --subject "Hello Fred" < msg.xxx
```

The connector script accepts the following arguments:

*   **-\-to** *email* ...    
    **-\-cc** *email* ...    
    **-\-bcc** *email* ...    

    One or more recipient email addresses.

*   **-\-subject** *text*

    Message subject.

*   **-\-text** *filename*

    File containing the text body of the message. Optional.

*   **-\-html** *filename*

    File containing the HTML body of the message. Optional.

If neither **--text** nor **--html** options are specified, the message body is
read from stdin. If the content begins with `<HTML>` (case insensitive), the
connector will send it as HTML otherwise as text.
