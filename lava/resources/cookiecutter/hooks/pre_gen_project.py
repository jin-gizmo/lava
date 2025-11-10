"""Validation checker for lava job framework."""

import json
import sys

# The tojson hack is a crude form of escaping.
required_vars = {
    'project_dir': '{{ cookiecutter.project_dir | tojson }}',
    'description': '{{ cookiecutter.description | tojson }}',
    'owner': '{{ cookiecutter.owner | tojson }}',
    'realm': '{{ cookiecutter.realm | tojson }}',
    'job_prefix': '{{ cookiecutter.job_prefix | tojson }}',
    'payload_prefix': '{{ cookiecutter.payload_prefix | tojson }}',
    's3trigger_prefix': '{{ cookiecutter.s3trigger_prefix | tojson }}',
    'docker_prefix': '{{ cookiecutter.docker_prefix | tojson }}',
    'rule_prefix': '{{ cookiecutter.rule_prefix | tojson }}',
}

# Decode the JSON
required_vars = {k: json.loads(v) for k, v in required_vars.items()}

errors = []
for k, v in required_vars.items():
    if not v:
        errors.append(f'ERROR: {k} must be specified')

# Add field specific validations here

if errors:
    print('\n'.join(errors))
    sys.exit(1)

sys.exit(0)
