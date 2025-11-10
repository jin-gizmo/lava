#!/bin/bash

# Package the code bundle for lambda. It creates a complete code bundle
# containing all the necessary components to run the code.

PROG=$(basename "$0")
dir=.
LAVA_VERSION=$(python3 ../lava/version.py)

# -------------------------------------------------------------------------------
function usage {
	echo "Usage: $PROG [-h] [-d dir] lambda-name" >&2
}

function help {
	usage
	cat >&2 <<-!

	Create an AWS Lambda deployment package.

	Options:
	  -d dir	Put the bundle in the specified directory
	  -h		Print help and exit

	!
}

function error {
	echo "$PROG: $*" >&2
}


# -------------------------------------------------------------------------------
args=$(getopt d:h "$@")
[ $? -ne 0 ] && usage && exit 2
# shellcheck disable=SC2086
set -- $args
while true
do
	case "$1"
	in
		-d)	dir="$2"; shift 2;;
		-h)	help; exit 0;;
		--)	shift; break;;
		*)	echo Internal error; exit 13;;
	esac
done

[ $# -ne 1 ] && usage && exit 1
[ ! -d "$1" ] && error "$1: No such directory" && exit 1

APP="$1"
PACKAGE="${APP}-${LAVA_VERSION}.zip"
LOCAL_FILES="*.py"
LOCAL_MODULES="lava"

TMP=$(pwd)/.pkg.$$
PKGTMP=__pkg__.zip

# -------------------------------------------------------------------------------
z=3
trap '/bin/rm -rf $TMP; exit $z' 0
mkdir -p "$TMP"

# Copy the main code over
# shellcheck disable=SC2086
(cd "$APP" || exit 1; find $LOCAL_FILES | cpio -pdu --quiet "$TMP")

# Add the lava modules
(cd ..; find $LOCAL_MODULES | cpio -pdu --quiet "$TMP")

# Install the non-standard modules
python3 -m pip install --ignore-installed --target "$TMP" -r "$APP/requirements.txt"
[ $? -ne 0 ] && error "Could not install requirements" && z=1 && exit 1

# Create the code bundle

find "$TMP" -type d -exec chmod go+rx '{}' \;
find "$TMP" -type f -exec chmod go+r '{}' \;

(
	cd "$TMP" || exit 1
	zip -9 --quiet -r $PKGTMP \
		--exclude '*.pyc' \
		--exclude '__pycache__' \
		--exclude '*.swp' \
		--exclude '*.zip' \
		--exclude '*.so' \
		--exclude '*.tar.*' \
		-- \
		*
)

mv "$TMP/$PKGTMP" "$dir/$PACKAGE"
echo "Created $dir/$PACKAGE"
z=0
