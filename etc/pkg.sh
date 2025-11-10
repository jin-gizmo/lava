#!/bin/bash

# Package the code bundle for lava.  It creates a complete code bundle
# containing all the necessary components to run the code.

PROG=$(basename "$0")

APP=lava
LOCAL_FILES="
	lava-*
	requirements*.txt
	install.sh
	etc/jinja
	etc/dyn-put-item
	etc/yaml2json
	bin/*
	"
LOCAL_MODULES="lava"

PACKAGE=$APP.tar.bz2
package="$PACKAGE"
PKGTMP=__pkg__.tar.bz2
basedir=.

# -------------------------------------------------------------------------------
function usage {
	echo "Usage: $PROG [-h] [-m] [filename]" >&2
}

function help {
	usage
	cat >&2 <<-!

	Create a lava deployment package for deploying to a Linux (like) run
	environment. The result is a bzipped tar file containing the code bunde.

	Options:

	  -f filename	Name of the output file. The default is $PACKAGE.

	  -h		Print help and exit

	  -m		Include non-standard modules. If not specified, only the
	          	base code is included and the modules must be separately
	        	installed with "python3 -m pip install -r requirements.txt".

	  lava-dir	The lava code base directory. Defaults to current directory.

	!
}

function error {
	echo "$PROG: $*" >&2
}

function abort {
	error "ABORT: $*"
	exit 1
}

# Convert relative path to absolute
function abspath {
	cd "$1" || exit 1
	pwd
}

# -------------------------------------------------------------------------------
# shellcheck disable=SC2048,SC2086
args=$(getopt f:hm $*)
[ $? -ne 0 ] && usage && exit 2
# shellcheck disable=SC2086
set -- $args
while true
do
	case "$1"
	in
		-f)	package="$2"; shift 2;;
		-h)	help; exit 0;;
		-m)	modules="yes"; shift;;
		--)	shift; break;;
		*)	abort "Internal error: $1";;
	esac
done

[ $# -gt 1 ] && usage && exit 1
[ "$1" != "" ] && basedir="$1"
[ ! -d "$basedir/lava/handlers" ] && abort "Doesn't look like a lava code base directory"

# -------------------------------------------------------------------------------

z=3
TMP=$(abspath "$basedir")/.pkg.$$
trap '/bin/rm -rf $TMP; exit $z' 0
mkdir -p "$TMP"

(
	cd "$basedir" || abort "Cannot chdir to $basedir"

	# Copy the main code over
	# shellcheck disable=SC2086
	find $LOCAL_FILES | cpio -pdu --quiet $TMP
	# shellcheck disable=SC2086
	find $LOCAL_MODULES | cpio -pdu --quiet $TMP

	# Create the version file which is build date/time
	# echo "VERSION = '$(date)'" > $TMP/lava/version.py

	# Install the non-standard modules
	mkdir "$TMP/pylib"
	if [ "$modules" != "" ]
	then
		python3 -m pip install --ignore-installed --upgrade \
			--target "$TMP/pylib" -r requirements.txt
		python3 -m pip install --ignore-installed --upgrade \
			--target "$TMP/pylib" -r requirements-extra.txt
	fi
)

# Create the code bundle. With Oracle, cannot exclude *.so
(
	cd "$TMP" || exit 1
	tar -cjf $PKGTMP --exclude '*.pyc' \
		--exclude '__pycache__' \
		--exclude '*.swp' \
		--exclude '*.zip' \
		--exclude '*.tar.*' \
		--exclude '.DS_Store' \
		-- \
		*
)

mv "$TMP/$PKGTMP" "$package"
echo "Created $package"
z=0
