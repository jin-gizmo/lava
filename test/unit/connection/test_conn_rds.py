"""Test RDS related connection stuff."""

from urllib.parse import parse_qs

from lava.connection.rds import get_rds_creds_with_iam
from test.conftest import use_moto


# ------------------------------------------------------------------------------
@use_moto
def test_get_rds_creds_with_iam():

    host = 'mydb.somewhere.amazonaws.com'
    user = 'lava'
    port = 1234

    conn_spec = {
        'conn_id': 'test/rds',
        'description': 'Dummy conn spec',
        'enabled': True,
        'host': host,
        'port': port,
        'database': 'lavatest',
        'user': user,
    }

    auth_user, auth_token = get_rds_creds_with_iam(conn_spec)

    assert auth_user == user

    netloc, qs = auth_token.split('/', 1)
    assert netloc == f'{host}:{port}'
    assert qs.startswith('?')

    query = parse_qs(qs[1:])
    assert query['Action'] == ['connect']
    assert query['DBUser'] == [user]

    assert {'X-Amz-Signature', 'X-Amz-Credential', 'X-Amz-Signature'} <= set(query)
