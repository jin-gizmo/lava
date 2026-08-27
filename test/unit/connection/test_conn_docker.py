"""Tests for docker connector."""

from lava.connection.docker import *
from test.conftest import use_moto


# ------------------------------------------------------------------------------
@use_moto
def test_get_docker_registry_credentials_ecr(aws_account_id):

    conn_spec = {
        'conn_id': 'test/docker/ecr',
        'description': 'Docker ECR connection',
        'enabled': True,
        'registry': 'ecr',
        'type': 'docker',
    }

    result = get_docker_registry_credentials(conn_spec)
    assert result['username'] == 'AWS'
    assert result['password']
    assert result['registry'].startswith(aws_account_id)


# ------------------------------------------------------------------------------
@use_moto
def test_get_docker_registry_credentials_registry():
    aws_session = boto3.Session()
    password_param = 'docker-registry-test-password'
    password = 'whatever'
    username = 'fred'

    ssm = aws_session.client('ssm')
    ssm.put_parameter(Name=password_param, Type='SecureString', Value=password)
    conn_spec = {
        'conn_id': 'test/docker/some-registry',
        'description': 'Docker registry connection',
        'enabled': True,
        'registry': 'some-registry',
        'type': 'docker',
        'user': username,
        'password': password_param,
    }
    result = get_docker_registry_credentials(conn_spec)
    assert result['username'] == username
    assert result['password'] == password
    assert result['registry'] == conn_spec['registry']
