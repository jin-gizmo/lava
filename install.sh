#!/bin/bash

# Install Lava

PROG=$(basename "$0")
LAVA_BASE=/opt/lava
LAVA_BIN=/usr/local/bin

# This list is used to check that a target install dir to be cleaned is actually
# a lava install directory. The listed files/dirs must be present. This is a
# safety measure to prevent blowing away the wrong directory accidentally.
EXPECTED_LAVA_FILES=(
	lava
	pylib
	install.sh
	lava/version.py
)

# ------------------------------------------------------------------------------
function usage {
	cat >&2 <<!
Install lava from a prebuilt source package.

Usage: $PROG [-b bin-dir] [-d install-dir] [-h] source-pkg ...

Args:
    -c			Do a clean install by removing existing lava components
    			in the install area.

    -b bin-dir		Directory for executables. Default is $LAVA_BIN.

    -d install-dir	Base directory for installation. The default is $LAVA_BASE.

    -h			Print help and exit.

    source-pkg		Location of source package produced using "make pkg".
    			Can be on the local machine or in S3 (s3://....). If
			multiple values are provided, then the first one that
			exists will be used for the install.

!
}

# ------------------------------------------------------------------------------
function info {
	echo "$*"
}

function abort {
	echo "ABORT: $*" >&2
	exit 1
}

# ------------------------------------------------------------------------------
# Test if an S3 object exists.
function s3_exists {
	local key bucket
	bucket=$(echo "$1" | sed -e 's/^s3:\/\///' -e 's/\/.*//')
	key=$(echo "$1" | sed -e 's/^s3:\/\///' -e 's/[^\/]*\///')
	aws s3api head-object --bucket "$bucket" --key "$key" > /dev/null 2>&1
}

# Convert relative path to absolute
function abspath {
	cd "$1" || exit 1
	pwd
}

# Check if an existing target install dir is really a lava install dir.
function is_lava_installdir {
	for f in "${EXPECTED_LAVA_FILES[@]}"
	do
		[ ! -e "$1/$f" ] && return 1
	done
	return 0
}

# ------------------------------------------------------------------------------
# Process args. 

# shellcheck disable=SC2048,SC2086
args=$(getopt cb:d:h $*)
[ $? -ne 0 ] && usage && exit 1

lava_bin="$LAVA_BIN"
lava_base="$LAVA_BASE"
# shellcheck disable=SC2086
set -- $args
while true
do
	case "$1"
	in
		-h)	usage; exit 0;;
		-b)	lava_bin="$2"; shift 2;;
		-d)	lava_base="$2"; shift 2;;
		-c)	clean=yes; shift;;
		--)	shift; break;;
		*)	abort "Internal error";;
	esac
done

[ $# -eq 0 ] && usage && exit 1

# ------------------------------------------------------------------------------
# Get the source bundle

pkg=
for loc
do
	if [[ "$loc" =~ ^s3:// ]]
	then
		s3_exists "$loc" || continue

		# Download from S3
		info "Getting package from S3"
		z=3
		TMP=/tmp/$PROG.$$
		trap '/bin/rm -rf $TMP; exit $z' 0
		mkdir "$TMP" || abort "Cannot create $TMP"
		aws s3 cp --no-progress "$loc" "$TMP"
		pkg="$TMP/$(basename "$loc")"
		break
	elif [ -f "$loc" ]
	then
		pkg="$loc"
		break
	fi
done

[ "$pkg" == "" ] && abort "No install package found"
[[ "$pkg" =~ .*\.tar.bz2$ ]] || abort "$loc is not a lava bundle"
info "Source package is $loc"

# ------------------------------------------------------------------------------

shopt -s nullglob

# ------------------------------------------------------------------------------
# Clean any existing install

if [ "$clean" == "yes" ] && [ -e "$lava_base" ]
then
	
	is_lava_installdir "$lava_base" || \
		abort "$lava_base exists and does not look like a lava install dir"
	[ -e "$lava_base/.git" ] && abort "$lava_base looks like a repo directory"
	info "Cleaning $lava_base and $lava_bin/lava-*"
	/bin/rm -rf "$lava_base" || exit 1
	/bin/rm -f "$lava_bin"/lava-* || exit 1
fi

# ------------------------------------------------------------------------------
# Install the bundle

umask 022

mkdir -p "$lava_base" || abort "Cannot create $lava_base"
mkdir -p "$lava_bin" || abort "Cannot create $lava_bin"

info "Extracting code to $lava_base"
tar --no-same-owner -C "$lava_base" -xf "$pkg" || abort "Could not unpack code bundle"

info "Fixing permissions"
find "$lava_base" -type d -exec chmod go+rx '{}' \;
find "$lava_base" -type f -exec chmod go+r '{}' \;
chmod go+rx "$lava_base/lava-run" "$lava_base/lava/version.py"

# Mac OS has this non-standard way of applying permissions to a symlink itself
# rather than the target. Need to fix using non-standard chmod -h
case "$(uname -s)" in
	Darwin)
		info Fixing weird Mac OS permissions
		find "$lava_base" -type l -exec chmod -h go+rx '{}' \;
		;;
	*)	;;
esac

# Want absolute path for our symlinks
lava_abs=$(abspath "$lava_base")
PY_UTILS=$(
	find "$lava_abs/bin" -type f -perm -0100 | \
		xargs -r file | \
		awk -F: 'BEGIN { IGNORECASE=1 }; $2 ~ /Python script/ { print $1 }'
	)
NON_PY_UTILS=$(
	find "$lava_abs/bin" -type f -perm -0100 | \
		xargs -r file | \
		awk -F: 'BEGIN { IGNORECASE=1 }; $2 !~ /Python script/ { print $1 }'
	)
# shellcheck disable=SC2086
chmod go+rx $PY_UTILS $NON_PY_UTILS

info "Installing executables in $lava_bin"
for cmd in $PY_UTILS
do
	base=$(basename "$cmd")
	[ -L "$lava_bin/$base" ] && /bin/rm -f "$lava_bin/$base"
	# lava-run manipulates PYTHONPATH then runs the script
	ln -s "$lava_abs/lava-run" "$lava_bin/$base"
done

for cmd in $NON_PY_UTILS
do
	base=$(basename "$cmd")
	[ -L "$lava_bin/$base" ] && /bin/rm -f "$lava_bin/$base"
	ln -s "$cmd" "$lava_bin/$base"
done

z=0
