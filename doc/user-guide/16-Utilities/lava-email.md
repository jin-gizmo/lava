
## Lava Email Utility { data-toc-label="lava-email" }

The **lava-email** utility uses the lava [email](#connector-type-email)
connector to send emails.

??? "Usage"

    ```bare
    usage: lava-email [-h] [--profile PROFILE] [-v] -c CONN_ID [-r REALM]
                      [-a FILE] [--bcc EMAIL] [--cc EMAIL] [--from EMAIL]
                      [--reply-to EMAIL] [--to EMAIL] -s SUBJECT [--html FILENAME]
                      [--text FILENAME] [--no-colour] [-l LEVEL] [--log LOG]
                      [--tag TAG]
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
      -a FILE, --attach FILE
                            Add the specified file as an attachment. Can be a
                            local file or an object in S3 in the form
                            s3://bucket/key. Can be used multiple times.
      --bcc EMAIL           Recipients to place on the Bcc: line of the message.
                            Can be used multiple times.
      --cc EMAIL            Recipients to place on the Cc: line of the message.
                            Can be used multiple times.
      --from EMAIL          Message sender. If not specified, a value must be
                            available in either the connection specification or
                            the realm specification.
      --reply-to EMAIL      Reply-to address of the message. Can be used multiple
                            times.
      --to EMAIL            Recipients to place on the To: line of the message.
                            Can be used multiple times.
      -s SUBJECT, --subject SUBJECT
                            Message subject. Required.

    message source arguments:
      At most one of the following arguments is permitted.

      --html FILENAME       This is a legacy argument for backward compatibility.
      --text FILENAME       This is a legacy argument for backward compatibility.
      FILENAME              Name of file containing the message body. If not
                            specified or "-", the body will be read from stdin. An
                            attempt is made to determine if the message is HTML
                            and send it accordingly. Only the first 2MB is read.

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
                            is lava-email.
    ```
