"""
Run a docker container.

The payload is an image identifier.

"""

from __future__ import annotations

import logging
import os
import re
import shlex
import sys
from tempfile import NamedTemporaryFile
from typing import Any
from uuid import uuid4

import boto3
import docker
import docker.errors
import jinja2
import requests.exceptions

from lava.config import LOGNAME, STATUS_TIMEOUT, config
from lava.connection import get_cli_connection, get_docker_connection
from lava.lavacore import DEFER_ON_EXIT, LavaError, jinja_render_vars, job_environment
from lava.lib.aws import s3_split, s3_upload
from lava.lib.datetime import duration_to_seconds
from lava.lib.misc import Defer, Task, dict_check

__author__ = 'Murray Andrews'

LOG = logging.getLogger(name=LOGNAME)

JOB_PARAMS_REQUIRED_FIELDS = None
JOB_PARAMS_OPTIONAL_FIELDS = {
    'args',
    'command',
    'connections',
    'docker',
    'env',
    'host_config',
    'jinja',
    'timeout',
    'vars',
}

HOST_CONFIG_OPTIONAL_FIELDS = {
    'blkio_weight_device',
    'blkio_weight',
    'cap_add',
    'cap_drop',
    'cpu_count',
    'cpu_percent',
    'cpu_period',
    'cpu_quota',
    'cpu_shares',
    'cpuset_cpus',
    'cpuset_mems',
    'device_read_bps',
    'device_read_iops',
    'device_write_bps',
    'device_write_iops',
    'dns',
    'dns_opt',
    'dns_search',
    'domainname',
    'extra_hosts',
    'hostname',
    'group_add',
    'mem_limit',
    'mem_swappiness',
    'memswap_limit',
    'nano_cpus',
    'network_disabled',
    'network_mode',
    'ports',
    'publish_all_ports',
    'shm_size',
    'user',
    'working_dir',
}


# ------------------------------------------------------------------------------
def run(
    job_spec: dict[str, Any],
    realm_info: dict[str, Any],
    tmpdir: str,
    s3tmp: str,
    dev_mode: bool = False,
    aws_session: boto3.Session = None,
) -> dict[str, Any]:
    """
    Run a container from an image whose name is the payload.

    The output is dropped in the s3tmp area.

    Allowed job parameters are:

    - args
        A list of zero or more arguments. Optional.

    - command
        The main executable / entry point in the image. If not specified, the
        default entry point is used.

    - connections
        A dictionary with keys that are connection labels and the values are
        conn_id. Optional.

    - docker
        conn_id for the docket registry. If not specified, a value must be
        specified at the realm level.

    - env
        A map of environment variables.

    - host_config
        Host configuration parameters for the container.

    - timeout
        Run timeout for the containter. It's a really bad idea to make this
        longer than the visibility period on the worker queue.

    - vars
        An optional dictionary of variables to use when Jinja rendering the
        args.

    :param job_spec:        The job spec from the DynamoDB database.
    :param realm_info:      Realm specific parameters.
    :param tmpdir:          A local temporary directory.
    :param s3tmp:           A prefix in S3 where temporary assets can be created
                            and left for others to pick up for limited time.
    :param dev_mode:        If True, emit stdout/stderr locally instead of
                            sending to S3. Default False.
    :param aws_session:     A boto3 Session()

    :return:                A dictionary of parameters that are available to
                            on-success, on-error, on-retry handlers.
    """

    if not aws_session:
        aws_session = boto3.Session()

    # ----------------------------------------
    # Validate the job spec

    parameters = job_spec.get('parameters', {})

    try:
        dict_check(
            parameters, required=JOB_PARAMS_REQUIRED_FIELDS, optional=JOB_PARAMS_OPTIONAL_FIELDS
        )
    except ValueError as e:
        raise LavaError(f'Bad job parameters: {e}')

    if ':' in job_spec['payload']:
        try:
            image_repo, image_tag = job_spec['payload'].strip().split(':')
        except ValueError:
            raise LavaError(
                f'Bad payload: {job_spec["payload"]}: Must be in the form repository[:tag]'
            )
    else:
        image_repo = job_spec['payload'].strip()
        image_tag = 'latest'

    timeout = duration_to_seconds(parameters.get('timeout', config('DOCKER_TIMEOUT')))

    host_config = parameters.get('host_config', {})
    host_config.setdefault('working_dir', tmpdir)
    # Run as host effective UID and effective group ID
    host_config.setdefault('user', os.geteuid())
    host_config.setdefault('group_add', [os.getegid()])
    host_config.setdefault('hostname', 'lava-{realm}-{worker}-{run_id}'.format(**job_spec)),

    try:
        dict_check(host_config, optional=HOST_CONFIG_OPTIONAL_FIELDS)
    except ValueError as e:
        raise LavaError(f'Bad host_config parameters: {e}')

    # ----------------------------------------
    # Prepare for Jinja rendering

    job_vars = parameters.get('vars', {})
    if not isinstance(job_vars, dict):
        raise LavaError('vars must be a map/dict')
    enable_jinja = parameters.get('jinja', True)
    render_vars = jinja_render_vars(job_spec, realm_info, vars=job_vars)

    # ----------------------------------------
    # Prepare the command to run. If not specified, use the container entry point.

    command = parameters.get('command')
    if command:
        command = shlex.split(command) + [str(a) for a in parameters.get('args', [])]
        if enable_jinja:
            try:
                # Render the args
                command = [jinja2.Template(a).render(**render_vars) for a in command]
            except Exception as e:
                raise LavaError(f'Bad command or args: {e}')

    LOG.debug('Command: %s', command)

    # ----------------------------------------
    # Prepare the environment

    env = job_environment(
        job_spec,
        realm_info,
        base={k: v for k, v in os.environ.items() if k.startswith('LAVA_')},
        render_vars=render_vars if enable_jinja else None,
        LAVA_S3_TMP=s3tmp,
        LAVA_S3_PAYLOAD=realm_info['s3_payloads'] + '/' + job_spec['payload'],
        LAVA_TMP=tmpdir,  # This will be mapped into the container
    )
    # LOG.debug('Command environment: %s', env)  # noqa: ERA001

    # ----------------------------------------
    # Get connections. These are the same CLI connections as are available to
    # pkg and exe jobs. They get mapped inside the container at the exact same
    # location as the local file system.

    if not isinstance(parameters.get('connections', {}), dict):
        raise LavaError('connections parameter must be a map')

    for conn_label, conn_id in parameters.get('connections', {}).items():
        if not re.fullmatch(r'\w+', conn_label):
            raise LavaError(f'Bad connection label: {conn_label}')
        connector = get_cli_connection(
            conn_id, job_spec['realm'], workdir=tmpdir, aws_session=aws_session
        )
        LOG.debug('CONN %s', connector)
        env.update(
            {
                'LAVA_CONNID_' + conn_label.upper(): conn_id,
                'LAVA_CONN_' + conn_label.upper(): connector,
            }
        )

    # ----------------------------------------
    # For volumes, we just map the local lava tmp dir into the same location
    # in the container.

    volumes = {tmpdir: {'bind': tmpdir, 'mode': 'rw'}}

    # ----------------------------------------
    # Get a connection to docker.

    docker_conn_id = parameters.get('docker', realm_info.get('docker'))
    if not docker_conn_id:
        raise LavaError('docker connection ID must be specified at the job or realm level.')

    try:
        LOG.debug('Creating docker connection for %s', docker_conn_id)
        dclient = get_docker_connection(
            docker_conn_id,
            realm=job_spec['realm'],
            # This seems to cause lots of problems -- use the detault instead
            # | config_dir=tmpdir,
            aws_session=aws_session,
        )

        LOG.debug(
            'Got docker connection (Name={Name}, IndexServer={IndexServerAddress}'.format(
                **dclient.info()
            )
        )
    except Exception as e:
        raise LavaError(f'Cannot get docker client: {e}')

    cntnr = None
    return_info = {'exit_status': 0}
    short_id = None

    try:
        # ------------------------------------
        # Pull the docker image
        try:
            LOG.debug('Pulling image %s:%s', image_repo, image_tag)
            # noinspection PyUnresolvedReferences
            image = dclient.images.pull(repository=image_repo, tag=image_tag)
            LOG.debug('Got image %s', image.tags)
        except docker.errors.APIError as e:
            # Hacksville -- Sometimes docker login works but the pull fails.
            # The workaround seems to be to try the login again.
            if e.is_error() and e.status_code in (404, 500):
                try:
                    LOG.warning(
                        f'Docker login ok but pull image failed: Error {e.status_code}:'
                        f' {image_repo}:{image_tag} - will try to login again',
                        extra={
                            'event_type': 'job',
                            'job_id': job_spec['job_id'],
                            'run_id': job_spec['run_id'],
                        },
                    )
                    dclient = get_docker_connection(
                        docker_conn_id, realm=job_spec['realm'], aws_session=aws_session
                    )
                    # noinspection PyUnresolvedReferences
                    image = dclient.images.pull(repository=image_repo, tag=image_tag)
                    LOG.debug('Got image %s on second attempt', image.tags)
                except Exception as e:
                    raise LavaError(f'Cannot pull docker image {image_repo}: {e}')
            else:
                raise LavaError(f'Cannot pull docker image {image_repo}: {e}')

        except docker.errors.DockerException as e:
            raise LavaError(f'Cannot pull docker image {image_repo}: {e}')

        # ------------------------------------
        # Create a container from the image.

        try:
            # noinspection PyUnresolvedReferences
            cntnr = dclient.containers.run(
                image=image,
                name=f'lava-{uuid4()}',
                command=command,
                detach=True,
                labels={
                    'lava.realm': job_spec['realm'],
                    'lava.worker': job_spec['worker'],
                    'lava.owner': job_spec['owner'],
                    'lava.job_id': job_spec['job_id'],
                    'lava.run_id': job_spec['run_id'],
                },
                stdout=True,
                stderr=True,
                environment=env,
                volumes=volumes,
                use_config_proxy=True,
                **host_config,
            )
        except docker.errors.DockerException as e:
            raise LavaError(f'Cannot run container from image {image_repo}: {e}')

        short_id = cntnr.id[:12]
        LOG.debug('Created container %s', short_id)

        # ------------------------------------
        # Wait for the container to finish.

        deferred_task_id = Defer.on_event(DEFER_ON_EXIT).add(
            Task(f'Kill container {short_id} (Run ID: {job_spec["run_id"]})', cntnr.stop)
        )

        try:
            return_info['exit_status'] = cntnr.wait(timeout=timeout).get('StatusCode', 0)
        except requests.exceptions.ConnectionError:
            return_info['exit_status'] = STATUS_TIMEOUT
            return_info['error'] = f'Timed out after {timeout} seconds'
        except Exception as e:
            return_info['exit_status'] = 1
            return_info['error'] = str(e)

        LOG.info(
            'Container %s: Status = %s',
            short_id,
            cntnr.status,
            extra={'event_type': 'job', 'job_id': job_spec['job_id'], 'run_id': job_spec['run_id']},
        )
        failed = bool(return_info['exit_status'])

        Defer.on_event(DEFER_ON_EXIT).cancel(deferred_task_id)

        # ------------------------------------
        # Seems like we have to force stop the container.
        if failed and cntnr:
            try:
                cntnr.stop()
                LOG.info(
                    'Stopped container %s',
                    short_id,
                    extra={
                        'event_type': 'job',
                        'job_id': job_spec['job_id'],
                        'run_id': job_spec['run_id'],
                    },
                )
            except Exception as e:
                LOG.error(
                    'Could not stop container %s: %s',
                    short_id,
                    e,
                    extra={
                        'event_type': 'job',
                        'job_id': job_spec['job_id'],
                        'run_id': job_spec['run_id'],
                    },
                )

        # ------------------------------------
        # Success or fail, copy any output to S3. Note that the result info
        # is passed as data to the exception on failure.
        logfp = None

        if dev_mode:
            for line in cntnr.logs(stream=True):
                sys.stdout.write(line.decode('utf-8'))
        else:
            with NamedTemporaryFile(dir=tmpdir, delete=False, suffix='.logs') as logfp:
                for line in cntnr.logs(stream=True):
                    logfp.write(line)

        if logfp and os.path.getsize(logfp.name) > 0:
            s3bucket, s3prefix = s3_split(s3tmp)
            s3key = f'{s3prefix}/logs'
            s3 = aws_session.client('s3')
            s3_upload(s3bucket, s3key, logfp.name, s3, kms_key=realm_info.get('s3_key'))
            return_info['output'] = f's3://{s3bucket}/{s3key}'
            LOG.debug('Uploaded %s to %s', logfp.name, return_info['output'])

        if failed:
            raise LavaError(
                f'Failed with exit status {return_info["exit_status"]}', data=return_info
            )

    except Exception:
        raise
    finally:
        # NOTE: This will get executed as part of the Defer() process.
        # WARNING: Need to keep an eye on this as potential for memory leak.
        if cntnr:
            try:
                cntnr.remove(force=True)
                LOG.debug('Removed container %s', short_id)
            except Exception as e:
                LOG.error('Could not remove container %s: %s', short_id, e)
        dclient.close()
        LOG.debug('Closed docker connection')

    return return_info
