# Makefile to build the lava AMI

SHELL:=/bin/bash
BASE=..
export PATH:=$(BASE)/etc:$(PATH)
LAVA_VERSION:=$(shell $(BASE)/lava/version.py)
DIST:=$(BASE)/dist
PARAMS=_ip _region _s3bucket _s3prefix _sg _subnet _tz _lava_version _python_version _ami_id _os _arch _instance_type
export PACKER_LOG=1

# ------------------------------------------------------------------------------
# Formatting
# Reset
F0=[0m
# Header
Fh=[31m
# Emphasis
Fe=[3m
# Literal
Fl=[4m[2m


# ------------------------------------------------------------------------------
# User specifiable parameters

s3bucket=
s3prefix=
subnet=
ip=
sg=
region:=$(shell aws configure get region)
tz=
python_version=
# os tells us the builder to use. It is OS specific but not architecture specific.
os=
# The type tells us OS and architecture and is used to derive base AMI ID.
type=
ami_ref=
ami_id=
arch=x86_64

# ------------------------------------------------------------------------------
# Extract a value from the config file or realm info
# Usage: $(call get_config,var-name)
get_config=$(shell echo '+{$(1)}+' | $(BASE)/etc/jinja -d+ --file $(config))

# ------------------------------------------------------------------------------

.PHONY: $(PARAMS) _ami ami all help

all:	help

#..............................................................................
# ... if config ...
ifdef config

ifdef env

export PACKER_LOG_PATH:=$(DIST)/ami/$(env)-$(shell date +%Y-%m-%dT%H:%M:%S).log
PACKER_MANIFEST:=$(DIST)/ami/$(env)-manifest.json

# Get what config we can from the config file
os=$(call get_config,$(env).ami.os)
__arch=$(call get_config,$(env).ami.arch)
ifneq ($(__arch),)
arch=$(__arch)
endif

ifeq ($(instance_type_),)
instance_type=$(shell echo "{{ arch.$(arch).instance_type }}" | jinja -f ami-build.yaml)
endif

__ami_name=$(shell echo "{{ os.$(os).ami_ref }}" | jinja -f ami-build.yaml)
ami_ref=$(shell echo "$(__ami_name)" | jinja -p arch="$(arch)")

ami_id:=$(shell aws ssm get-parameter --name /aws/service/ami-amazon-linux-latest/$(ami_ref) --query 'Parameter.Value' --output text)
subnet=$(call get_config,$(env).ami.subnet)
ip:=$(call get_config,$(env).ami.ip)
sg:=$(call get_config,$(env).ami.sg)
tz:=$(call get_config,$(env).ami.tz)
python_version=$(call get_config,$(env).ami.python.version)
python_short_version=$(shell echo "$(python_version)" | cut -f1,2 -d.)

s3loc=$(call get_config,$(env).ami.s3)
s3base=$(call get_config,$(env)._.s3base)


# This weirdness is to handle the odd S3 structure in the deploy file.
ifneq ($(s3loc),)
s3bucket:=$(shell $(BASE)/etc/s3loc -/ -f '{{b}}' "$(s3loc)" "$(s3base)")
s3prefix:=$(shell $(BASE)/etc/s3loc -/ -f '{{k}}' "$(s3loc)" "$(s3base)")
endif

ami:	_ami

else
ami:
	$(error Either both of config/env need to be specified or neither)
endif

# ... else not config
else

ifdef env
ami:
	$(error Either both of config/env need to be specified or neither)
else
ami:	_ami
endif


export PACKER_LOG_PATH:=$(DIST)/ami/$(shell date +%Y-%m-%dT%H:%M:%S).log
PACKER_MANIFEST:=$(shell aws sts get-caller-identity --query Account --output text)-manifest.json

# ... end config
endif

ifeq ($(ip),public)
associate_public_ip=true
else
associate_public_ip=false
endif


#..............................................................................
help:
	@echo "What do you want to make?"
	@echo
	@echo "$(Fh)Available Targets:$(F0)"
	@echo "    ami          Make the lava AMI."
	@echo "    help         Print help and exit."
	@echo
	@echo "$(Fh)Recommended Usage:$(F0)"
	@echo "    make ami config=deploy/___.yaml env=___"
	@echo
	@echo "$(Fh)Required Config Parameters:$(F0)"
	@echo "    The following parameters are required. They can be provided directly"
	@echo "    as $(Fl)param=value$(F0) conventional make(1) parameters or they can be provided"
	@echo "    from a config file using the $(Fl)config$(F0) and $(Fl)env$(F0) parameters."
	@echo
	@echo "    os           The OS type of AMI to be built. See ami-build.yaml. Must be one of:" 
	@( \
		echo '{%- for f in os %}                 - $(Fl){{ f }}$(F0) : {{ os[f].description }}' ; \
		echo '{% endfor -%}' ; \
	) | jinja -f ami-build.yaml
	@echo "    ip           IP address type for the packer build instance. Either"
	@echo "                 $(Fl)public$(F0) or $(Fl)private$(F0)."
	@echo "    python_version"
	@echo "                 The Python version to build from source for the AMI (e.g. $(Fl)3.11.13$(F0))."
	@echo "    s3bucket     S3 bucket containing extra build resources such as the Oracle bundles."
	@echo "    s3prefix     S3 prefix containing extra build resources such as the Oracle bundles."
	@echo "    sg           Security group ID (or a comma separated list of IDs)"
	@echo "                 for the packer build instance."
	@echo "    subnet       Subnet ID for the packer build instance."
	@echo "    tz           Timezone to set in instances created from the lava AMI."
	@echo
	@echo "$(Fh)Optional Config Parameters:$(F0)"
	@echo "    ami_id       ID of the base AMI. Defaults to the $(Fe)latest$(F0) AMI with the name"
	@echo "                 specified by the $(Fl)ami_ref$(F0) parameter. Note that AWS is tricksy on"
	@echo "                 this and the so-called latest may not have the latest kernel version."
	@echo "    ami_ref      The AWS SSM parameter name containing the ID the base AMI"
	@echo "                 (e.g. $(Fl)al2023-ami-kernel-default-x86_64$(F0)). AWS provides"
	@echo "                 a bunch of these parameters to simplify finding common AMIs."
	@echo "                 See https://docs.aws.amazon.com/linux/al2023/ug/ec2.html".
	@echo "    arch         CPU architecture. Must be one of:"
	@( \
		echo '{%- for a in arch %}                 - $(Fl){{ a }}$(F0)' ; \
		echo '{% endfor -%}' ; \
	) | jinja -f ami-build.yaml
	@echo "    config       Name of a YAML config file (in lava deploy format) containing"
	@echo "                 values for any or all of the required parameters. If specified,"
	@echo "                 the $(Fl)env$(F0) parameter is also required."
	@echo "    env          The environment identifier within a specified config file."
	@echo "    instance_type"
	@echo "                 The build instance type. Defaults to whatever is specified in ami-build.yaml."
	@echo


$(DIST)/ami:
	mkdir -p $@

_ami:	$(PARAMS) $(DIST)/ami
	@touch $(PACKER_LOG_PATH)
	packer build \
		-var ami_id="$(ami_id)" \
		-var arch="$(arch)" \
		-var associate_public_ip="$(associate_public_ip)" \
		-var os="$(os)" \
		-var instance_type="$(instance_type)" \
		-var ip="$(ip)" \
		-var subnet="$(subnet)" \
		-var security_group_ids="$(sg)" \
		-var region="$(region)" \
		-var python_version="$(python_version)" \
		-var python_short_version="$(python_short_version)" \
		-var timezone="$(tz)" \
		-var s3bucket="$(s3bucket)" \
		-var s3prefix="$(s3prefix)" \
		-var lava_version="$(LAVA_VERSION)" \
		-var logfile="$(PACKER_LOG_PATH)" \
		-var repo="$$(git config --get remote.origin.url)" \
		-var manifest="$(PACKER_MANIFEST)" \
		lava-ami.json


#..............................................................................
# Packer var validators
_ami_id:
	@if [ "$(ami_id)" == "" ] ; \
	then \
		echo "ami_id must be set to the base AMI ID. Try make $(MAKECMDGOALS) ami_id=..." >&2 ; \
		exit 1 ; \
	else : ; \
	fi

_arch:
	@if [ "$(arch)" == "" ] ; \
	then \
		echo "arch must be set. Try make $(MAKECMDGOALS) arch=..." >&2 ; \
		exit 1 ; \
	else : ; \
	fi

_os:
	@if [ "$(os)" == "" ] ; \
	then \
		echo "os must be set. Try make $(MAKECMDGOALS) os=..." >&2 ; \
		exit 1 ; \
	else : ; \
	fi

_instance_type:
	@if [ "$(instance_type)" == "" ] ; \
	then \
		echo "instance_type must be set. Try make $(MAKECMDGOALS) instance_type=..." >&2 ; \
		exit 1 ; \
	else : ; \
	fi

_ip:
	@if [ "$(ip)" != public -a "$(ip)" != private ] ; \
	then \
		echo "ip must be set to public or private. Try make $(MAKECMDGOALS) ip=..." >&2 ; \
		exit 1 ; \
	else : ; \
	fi

_s3bucket:
	@if [ "$(s3bucket)" == "" ] ; \
	then \
		echo "s3bucket must be set to the S3 bucket containing extra build components (e.g. Oracle)." \
			"Try make $(MAKECMDGOALS) s3bucket=..." >&2 ; \
		exit 1 ; \
	else : ; \
	fi

_s3prefix:
	@if [ "$(s3prefix)" == "" ] ; \
	then \
		echo "s3prefix must be set to the S3 prefix containing extra build components (e.g. Oracle)." \
			"Try make $(MAKECMDGOALS) s3bucket=..." >&2 ; \
		exit 1 ; \
	else : ; \
	fi
	@if [[ "$(s3prefix)" != */ ]] ; \
	then \
		echo "s3prefix must end with /" >&2 ; \
		exit 1 ; \
	else : ; \
	fi

_subnet:
	@if [ "$(subnet)" == "" ] ; \
	then \
		echo "subnet must be set to the build subnet ID. Try make $(MAKECMDGOALS) subnet=..." >&2 ; \
		exit 1 ; \
	else : ; \
	fi

_sg:
	@if [ "$(sg)" == "" ] ; \
	then \
		echo "sg must be set to a comma separated list of security group IDs. Try make $(MAKECMDGOALS) sg=..." >&2 ; \
		exit 1 ; \
	else : ; \
	fi

_region:
	@if [ "$(region)" == "" ] ; \
	then \
		echo "region must be set to the target AWS region. Try make $(MAKECMDGOALS) region=..." >&2 ; \
		exit 1 ; \
	else : ; \
	fi

_tz:
	@if [ "$(tz)" == "" ] ; \
	then \
		echo "tz must be set to the timezone on instances of the new AMI. Try make $(MAKECMDGOALS) tz=..." >&2 ; \
		exit 1 ; \
	else : ; \
	fi

_python_version:
	@if [ "$(python_version)" == "" ] ; \
	then \
		echo "python_version must be set to the Python version. Try make $(MAKECMDGOALS) python_version=..." >&2 ; \
		exit 1 ; \
	else : ; \
	fi
