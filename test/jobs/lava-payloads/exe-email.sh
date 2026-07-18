#!/bin/bash

# Requires an email connector "email"

[ $# -ne 1 ] && echo "Usage: $0 email-address" >&2 && exit 1

z=3
MSGFILE=msg.html
trap '/bin/rm -f $MSGFILE; exit $z' 0

echo "<HTML><BODY><h1>Environment</h1><bl>" > $MSGFILE

env | sed -e 's?.*?<li>&</li>?' >> $MSGFILE

echo "<bl></body></html>" >> $MSGFILE

cat $MSGFILE

echo "CONN IS '$LAVA_CONN_EMAIL'"
echo "++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
cat $LAVA_CONN_EMAIL
echo "++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
set -x

$LAVA_CONN_EMAIL --level debug --to "$1" --subject "HTML: $LAVA_JOB_ID($LAVA_RUN_ID)" < $MSGFILE
$LAVA_CONN_EMAIL --level debug --to "$1" --subject "TEXT: $LAVA_JOB_ID($LAVA_RUN_ID)" < /etc/hosts

# Now for an attachment. Filename to attach is in the ATTACH env var.
$LAVA_CONN_EMAIL --level debug --to "$1" --subject "ATTACH: $LAVA_JOB_ID($LAVA_RUN_ID)" --attach "$ATTACH" <<!
<HTML>
    <BODY>
        <H1>Attachment Test</H1>
	<P>
	    This email was sent by an exe job using the CLI connector.
	    It should have an attachment.
	</P>
    </BODY>
</HTML>
!

z=0
