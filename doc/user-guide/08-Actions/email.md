
## Action type: email

The **email** action uses either the [email](#connector-type-email) or a
bare-metal AWS Simple Email Service (SES) default to send an email
message.

|Field|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|action|String|Yes|The action type: `email`.|
|attachments|List\[string]|No|A list of file names to add as attachments. If specified, `email_conn` must also be specified, as the default bare-metal AWS SES sender does not support attachments. Files can be local or in S3 (`s3://...`). Each filename is individually Jinja rendered. **Be careful** with this to avoid using untrusted globals in filenames.|
|email\_conn|String|No|The name of an [email](#connector-type-email) connector to use for sending email. If not specified, then bare-metal AWS SES is used.|
|from|String|No|The source email address. If not specified, lava will defer to the `email_conn` connector if specified, or else look for a value in the realm specification (see below) or construct a default by scanning the SES configuration for validated domains.|
|message|String|Yes|The message body. If the message text begins with `<HTML>` (case-insensitive), it is sent as a HTML message body, otherwise as text. This is Jinja rendered prior to use.|
|region|String|No|The AWS region name for the SES service. If not specified, lava will look for a value in the realm specification (see below) or use the default of `us-east-1`. Ignored if `email_conn` is specified.|
|subject|String|Yes|The message subject. This is Jinja rendered prior to use.|
|to|String _or_ List[String]|Yes|The destination email address(es).|

The Jinja rendered action parameters have the following variables injected.

|Name|Type|Description|
|-|-|-------------------------------------------------------------|
|globals|dict[str,\*]|The globals map for the job that triggered the action.|
|job|dict[str,\*]|The [augmented job specification](#the-augmented-job-specification) for the job that triggered the action.|
|realm|dict[str,\*]|The realm specification.|
|result|dict[str,\*]|The result object from the job that triggered the action.|
|start|datetime|The local time when the job run started.|
|state|dict[str,\*]|A dictionary of the state items imported into the job, keyed on state_id. The default values are updated at run-time with any current values obtainable from the [state](#the-state-table) table.|
|ustart|datetime|The UTC time when the job run started.|
|utils|dict[str,runnable]|A dictionary of [utility functions](#jinja-utility-functions) that can be used in the Jinja markup.|

Refer to [Jinja Rendering in Lava](#jinja-rendering-in-lava)
for more information.

Default values for some of the fields required for the **email** action to use
AWS SES can be set in the [realms table](#the-realms-table) by setting
entries in the `config` realm entry, thus:

```json
{
  "...": "... other realm related elements ...",
  "config": {
    "ses_region": "... SES region name ...",
    "ses_from": "... Default source email address"
  }
}
```
