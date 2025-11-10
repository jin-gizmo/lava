#!/bin/bash

# Sync Oracle package zips from their download site.

export PATH=.:$PATH
PROG=$(basename "$0")

BASE_URL=https://download.oracle.com/otn_software/linux/instantclient

PACKAGES=(
	# ----------------------------------------
	# Arm

	instantclient-basic-linux-arm64.zip
	instantclient-basiclite-linux-arm64.zip
	instantclient-sqlplus-linux-arm64.zip

	# instantclient-odbc-linux-arm64.zip
	# instantclient-sdk-linux-arm64.zip
	# instantclient-tools-linux-arm64.zip

	# ----------------------------------------
	# x86

	instantclient-basic-linuxx64.zip
	instantclient-basiclite-linuxx64.zip
	instantclient-sqlplus-linuxx64.zip

	# instantclient-odbc-linuxx64.zip
	# instantclient-sdk-linuxx64.zip
	# instantclient-tools-linuxx64.zip
)

OS=linux
TMP=$(mktemp -d)
z=1
trap '/bin/rm -rf "$TMP"; exit $z' 0

# ------------------------------------------------------------------------------
function usage {
	echo "Usage: $PROG [destination-directory]"
	echo
	echo "destination-directory defaults to the current directory."
}

# ------------------------------------------------------------------------------
# Get the version of the package in an Oracle package zip file. This is embedded
# in the name of the main directory in the zip. e.g. "instantclient_19_25/..."
function get_oracle_pkg_version {
	# Note we are using extended regex here to support +. This brings
	# slightly different capture group syntax with it.
	zipinfo -1 "$1" | sed -Ene '/_[0-9]+_[0-9]+\//{s?^[^/_]*_([0-9]+)_([0-9]+)/.*?\1.\2?;p;q;}'
	
}

# ------------------------------------------------------------------------------
# Oracle is not consistent with naming of download files. Sometimes the OS and
# architecture are separated by "-" (e.g. instantclient-basiclite-linux-arm64.zip)
# and sometimes there is no "-" (e.g. instantclient-basic-linuxx64.zip).
function normalise_oracle_filename {
	f="$1"
	if [[ "$f" =~ (.*$OS)([a-z0-9].*) ]]
	then
		echo "${BASH_REMATCH[1]}-${BASH_REMATCH[2]}"
	else
		echo "$f"
	fi
}

# ------------------------------------------------------------------------------
# Sync a downloadable Oracle package from the Oracle link to the latest package
# version. The URLs package come in with an un-versioned name like
# 	https://.../instantclient-basic-linuxx64.zip"
# In the local file system we want this versioned and normalised. The process is:
#
#   1.	Get a normalised local file name with a dash between O/S and architecture
#   2.	Check if there is an updated version at Oracle.
#   3.	Download it and move to a version form of the name like this:
#   	   instantclient-basic-linux-x64-23.7.zip
#   4.	Create a symlink from the unversioned (normalised) filename to the
#	versioned form.
#
# Usage: sync_oracle_download url [destdir]
function sync_oracle_download {
	local url="$1" asset unversioned_file versioned_file destdir

	asset="$(basename "$url")"
	unversioned_file="$(normalise_oracle_filename "$asset")"

	[ "$2" != "" ] && destdir="$2/"


	if [ -e "${destdir}${unversioned_file}" -a ! -L "${destdir}${unversioned_file}" ]
	then
		echo "${destdir}${unversioned_file} exists and is not a symlink -- cannot sync" >&2
		return 1
	fi
	web-sync --check "$url" "${destdir}${unversioned_file}" && return 0
	
	# Need to update
	web-sync "$url" "$TMP/$unversioned_file" || return 1
	version=$(get_oracle_pkg_version "$TMP/$unversioned_file")
	if [ $? -ne 0 -o "$version" == "" ]
	then
		echo "$asset: Cannot determine package version" >&2
		return 1
	fi
	versioned_file="${unversioned_file%.*}-${version}.${unversioned_file##*.}"
	if [ "$unversioned_file" == "$versioned_file" ]
	then
		echo "Versioned and unversiond file names are the same: $unversioned_file"
		return 1
	fi
	mv "$TMP/$unversioned_file" "${destdir}${versioned_file}" || return 1
	(
		cd "${destdir:-}" || exit 1
		/bin/rm -f "$unversioned_file" || exit 1
		ln -s "${versioned_file}" "${unversioned_file}"
	) || return 1
	return 0
}

# ------------------------------------------------------------------------------
[ $# -gt 1 ] && usage && exit 1
case "$1"
in
	-h | --help)
		usage; exit 0;;
	"")	;;
	*)
		[ ! -d "$1" ] && echo "$PROG: No such directory" && exit 1;;	
esac

for pkg in "${PACKAGES[@]}"
do
	sync_oracle_download "$BASE_URL/$pkg" "$1" || exit 1
done

z=0
