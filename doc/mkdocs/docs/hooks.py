"""Custom hooks for mkdocs."""

import datetime
import os


# ------------------------------------------------------------------------------
# noinspection PyUnusedLocal
def on_config(config, **kwargs):
    """Add dynamic values to config.extra."""

    config.extra['build_time'] = datetime.datetime.now().astimezone()
    config.extra['git_commit'] = os.popen('git rev-parse --short HEAD').read().strip()
    # Allows us to reference environment vars as {{ config.extra.environment.name }}
    config.extra['environment'] = os.environ

    return config
