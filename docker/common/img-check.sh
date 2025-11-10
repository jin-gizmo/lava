#!/bin/bash
# shellcheck disable=SC2317,SC2329

# Run some basic checks on a lava image

OPENSSL_MIN_VERSION=3

# ------------------------------------------------------------------------------
function usage {
	echo "Usage: $0 [-p platform] lava-docker-image"
}

# shellcheck disable=SC2048,SC2086
args=$(getopt p: $*)
if [ $? -ne 0 ]
then
	usage
	exit 2
fi
# shellcheck disable=SC2086
set -- $args

while true
do
	case "$1" in
		-p)	platform="$2"; shift 2 ;;
		--)	shift; break ;;
		*)	echo "check error"; exit 13 ;;
	esac
done
[ $# -ne 1 ] && usage && exit 2

image="$1"

# ------------------------------------------------------------------------------
function info {
	echo "[34m$*[0m"
}

function ok {
	echo "[32m$*[0m"
}

function warning {
	echo "[33m$*[0m"
}

function error {
	echo "[31m$*[0m"
}

function drun {
	if [ "$platform" = "" ]
	then
		docker run --pull never -i --rm "$image" "$@"
	else
		docker run --platform="$platform" --pull never -i --rm "$image" "$@"
	fi
}

function check {
	info "🔵 ${FUNCNAME[1]}: $*"
}

function get_funcs_by_regex {
	declare -F | cut -d' ' -f3 | grep "$1" | sort 
}

# ------------------------------------------------------------------------------
# These are the checking functions. Whether the checks are used for the base or
# full image is determined by the function name. Checks are auto discovered.
#
# chk_base_*:   These checks apply to the lava base image _and_ the full image.
# chk_full_*:   These checks apply only to the full image.

function chk_base_arch {
	check Platform architecture
	local arch actual_platform

	arch=$(drun arch) || return $?
	echo "Architecture is $arch"
	[ "$platform" = "" ] && return 0
	case "$arch"
	in
		x86_64)  actual_platform=linux/amd64 ;;
		aarch64) actual_platform=linux/arm64 ;;
		*)       error "Unknown architecture: $arch"; return 1 ;;
	esac
	if [ "$actual_platform" != "$platform" ]
	then
		error "Image platform is $actual_platform ($arch) not $platform"
		return 1
	fi
	return 0
}

function chk_base_lava {
	check lava version
	drun lava-worker --version || return $?
}

function chk_base_python {
	check Python version
	drun python3 --version || return $?
}

function chk_base_ssl {
	set -e
	check OpenSSL version
	ssl_ver=$(openssl --version)
	echo "$ssl_ver"
	if [[ $ssl_ver =~ OpenSSL[[:space:]]([0-9]+)\. ]]
	then
		if [ "${BASH_REMATCH[1]}" -lt "$OPENSSL_MIN_VERSION" ]
		then
			error "Expected OpenSSL version >= $OPENSSL_MIN_VERSION"
			return 1
		fi
	else
		error "Cannot work out OpenSSL version: $ssl_ver"
		return 1
	fi
	drun python3 -c 'import ssl; print("Python SSL:", ssl.OPENSSL_VERSION)' || return $?
}

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
function chk_full_psql {
	check psql CLI
	drun psql --version
}

function chk_full_mysql {
	check MySQL CLI
	drun mysql --version
}

function chk_full_sqlplus {
	check "SQL*Plus CLI"
	local image="$1"
	set -o pipefail
	# DOS line endings on sqlplus. Oracle never did have a clue about UNIX.
	drun sqlplus -V 2>&1 | sed -e '/^ *\r$/d'
	local status=$?
	if [ "$status" -ne 0 ]
	then
		case "$(arch)-$image" in
			arm64-dist/lava/amzn2/full)
				# sqlplus is known not to work and it's not worth fixing.
				warning "sqlplus is known not to work on $image"
				return 0
				;;
			*)	;;
		esac
	fi
	return "$status"
}

function chk_base_isql {
	check "isql (unixODBC)"
	drun isql --version
}

function chk_base_tsql {
	check "tsql (FreeTDS)"
	drun tsql -C
}

function chk_base_awscli {
	check AWS CLI
	drun aws --version
}

function chk_base_make {
	check make
	drun make --version
}

# ------------------------------------------------------------------------------
# shellcheck disable=SC2046
read -ra checks <<< $(get_funcs_by_regex '^chk_base_')
case "$image" in
	*lava/*/base)
		;;
	*lava/*/full)
		# shellcheck disable=SC2046
		read -ra full_checks <<< $(get_funcs_by_regex '^chk_full_')
		checks+=("${full_checks[@]}")
		;;
	*)	error "$image: Unknown lava image type"
		;;
esac

status=0
declare -a failed

for check in "${checks[@]}"
do
	if ! $check "$image"
	then
		error "❌ $check failed" && status=1
		failed+=("$check")
	else
		ok "✅ $check passed"
	fi
	echo
done

if [ $status -ne 0 ]
then
	error "--------------------------------------------------------------------------------"
	error "❌ $image ($platform): ${#failed[@]} error(s): ${failed[*]}"
	error "--------------------------------------------------------------------------------"
else
	ok "--------------------------------------------------------------------------------"
	ok "✅ $image ($platform): 0 errors"
	ok "--------------------------------------------------------------------------------"
fi
echo
exit $status
