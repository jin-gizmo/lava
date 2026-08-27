"""Test for the Redshift connector."""

from lava.connection.redshift import *
from test.conftest import use_moto


# ------------------------------------------------------------------------------
def create_redshift_cluster(cluster_id, redshift_client):
    """
    Create a Redshift cluster.

    This is intended for use in a moto context where it is quick and cheap to do.
    """

    response = redshift_client.create_cluster(
        DBName='lava',
        ClusterIdentifier=cluster_id,
        ClusterType='single-node',
        NodeType='dc2.large',
        MasterUsername='master',
        ManageMasterPassword=True,
        VpcSecurityGroupIds=['vpc-12345'],
    )
    return response


# ------------------------------------------------------------------------------
@use_moto
def test_get_redshift_cluster_creds_with_iam_ok(tc):
    cluster_id = 'rs-mock'
    db_name = 'lava'
    db_user = 'lavatest'
    conn_spec = {
        'conn_id': 'test/redshift-moto',
        'description': 'Mock redshift connection',
        'enabled': True,
        'type': 'redshift',
        'host': f'{cluster_id}.xyzzy.ap-southeast-2.redshift.amazonaws.com',
        'port': 5439,
        'database': db_name,
        'user': db_user,
    }
    rs = boto3.Session().client('redshift')
    create_redshift_cluster(cluster_id, rs)

    user, password = get_redshift_cluster_creds_with_iam(conn_spec)
    assert user == f'IAM:{db_user}'
    assert password
