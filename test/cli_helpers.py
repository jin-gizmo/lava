"""Helpers for dockerized database CLI fixtures."""

from __future__ import annotations

import shlex
from pathlib import Path

from test.const import DOCKER_NETWORK


# ------------------------------------------------------------------------------
def docker_cli_command(image: str, *paths: Path, network: str = DOCKER_NETWORK) -> str:
    """Build a docker run command for a CLI image with optional bind mounts."""

    volumes = ' '.join(f'-v {shlex.quote(str(d))}:{shlex.quote(str(d))}' for d in paths)
    cmd = f'docker run -i --rm --network {shlex.quote(network)}'
    if volumes:
        cmd += f' {volumes}'
    return f'{cmd} {shlex.quote(image)}'


# ------------------------------------------------------------------------------
def patch_mysql_cli_to_docker(
    monkeypatch,
    image: str,
    *paths: Path,
    network: str = DOCKER_NETWORK,
) -> None:
    """Patch the mysql connector to use a dockerized mysql CLI command."""

    # noinspection PyProtectedMember
    from lava.connection.mysql import _mysql_flavour

    monkeypatch.setattr('lava.connection.mysql._mysql_flavour', _mysql_flavour.__wrapped__)
    monkeypatch.setattr(
        'lava.connection.mysql.MYSQL_CLI',
        docker_cli_command(image, *paths, network=network),
    )


# ------------------------------------------------------------------------------
def patch_sqlplus_cli_to_docker(
    monkeypatch,
    image: str = 'sqlplus-cli',
    *paths: Path,
    network: str = DOCKER_NETWORK,
) -> None:
    """Patch the Oracle connector to use a dockerized sqlplus CLI command."""

    monkeypatch.setattr(
        'lava.connection.oracle.ORACLE_CLI',
        docker_cli_command(image, *paths, network=network),
    )


# ------------------------------------------------------------------------------
def patch_psql_cli_to_docker(
    monkeypatch,
    etc_dir: str | Path,
    image: str = 'psql-cli',
    *paths: Path,
    network: str = DOCKER_NETWORK,
) -> None:
    """Patch the Postgres connector to use a dockerized psql CLI command."""

    docker_run_env = shlex.quote(str(Path(etc_dir) / 'docker-run-env'))
    cli = (
        f'{docker_run_env} "^PG" -- '
        f'-i --rm --network {shlex.quote(network)} '
        f'{" ".join(f"-v {shlex.quote(str(d))}:{shlex.quote(str(d))}" for d in paths)} '
        f'{shlex.quote(image)}'
    ).strip()
    monkeypatch.setattr('lava.connection.postgres.PSQL_CLI', cli)