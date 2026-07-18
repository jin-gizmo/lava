"""Test config for connectors."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest  # noqa

from test.cli_helpers import (
    patch_mysql_cli_to_docker,
    patch_psql_cli_to_docker,
    patch_sqlplus_cli_to_docker,
)
from test.const import DOCKER_NETWORK


# ------------------------------------------------------------------------------
@pytest.fixture(scope='function')
def set_mysql_docker_cli(monkeypatch) -> Callable[[str, ...], None]:
    """
    Use the docker based mysql client.

    Usage as a fixture: docker_mysql_client('oracle', tmp_path)
    """

    def _cli(client_type: str, *path: Path):
        """
        Use the docker based mysql client.

        :param client_type: Either 'oracle' or 'mariadb'.
        :param workdir:     Working directory.
        """

        patch_mysql_cli_to_docker(
            monkeypatch,
            f'mysql-cli-{client_type}',
            *path,
            network=DOCKER_NETWORK,
        )

    return _cli


# ------------------------------------------------------------------------------
@pytest.fixture(scope='function')
def set_sqlplus_docker_cli(monkeypatch) -> Callable[[...], None]:
    """Use the docker based Oracle sqlplus client."""

    def _cli(*path: Path):
        """Use the docker based Oracle sqlplus client."""

        patch_sqlplus_cli_to_docker(monkeypatch, 'sqlplus-cli', *path, network=DOCKER_NETWORK)

    return _cli


# ------------------------------------------------------------------------------
@pytest.fixture(scope='function')
def set_psql_docker_cli(dirs, monkeypatch) -> Callable[[...], None]:
    """Use the docker based Postgres psql client."""

    def _cli(*path: Path):
        """Use the docker based Postgres psql client."""

        # Basically we're doing a docker run here but injecting all env vars
        # that start with PG into the container for use by psql.
        patch_psql_cli_to_docker(
            monkeypatch,
            dirs.etc,
            'psql-cli',
            *path,
            network=DOCKER_NETWORK,
        )

    return _cli
