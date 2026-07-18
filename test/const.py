"""Global test related constants."""

REALM = 'test'
WORKER = 'core'

DOCKER_NETWORK = 'lava-test'

# These are the marks in job based tests selected by default
TARGET_MARKS = ['local']

MAILPIT_SMTP_PORT = 1025
MAILPIT_ADMIN_PORT = 8025
MAILPIT_HOST = f'{DOCKER_NETWORK}-mail'
