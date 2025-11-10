
## Python Executable Jobs

In addition to the facilities available to all executable jobs, additional
functionality is available for Python jobs as lava itself is Python based.

Python based executable jobs can interface directly with the lava Python base
package. This provides access to the lava connection manager as well as other
modules included with lava.

See [Installing Lava Locally](#installing-lava-locally).


## Connection Handling for Python Based Jobs { data-toc-label="Connections in Python" }

Python based lava programs can invoke the lava connection manager directly.  See
[lava.connections][lava.connection] in the [API
documentation](#lava-api-reference) for more information.

This is a simple example showing how to create a connection to an SQL-based
database:

```python
import os
from lava.connection import get_pysql_connection

# As we are using the lava connection manager, we just need the connection ID
# this time – not the connector script. So use LAVA_CONNID_DB not LAVA_CONN_DB.

conn_id = os.environ['LAVA_CONNID_DB']
realm = os.environ['LAVA_REALM']

# Get a standard DBAPI 2.0 connection
conn = get_pysql_connection(conn_id, realm)

# Knock yourself out with SQL wizardry…
cursor = conn.cursor()
...
conn.close()
```

## Connection Handling for SQLAlchemy { data-toc-label="Connections in SQLAlchemy" }

The SQL [database connectors](#database-connectors) provide native
support for [SQLAlchemy](https://www.sqlalchemy.org/). An SQLAlchemy engine can
be created using a lava connector to manage the underlying connection process.

This is useful, not just for using SQLAlchemy natively, but also for packages
such as [pandas](https://pandas.pydata.org) that rely on SQLAlchemy for database
interaction.

The following example shows how this would be used.

```python
import os
import pandas as pd
from lava.connection import get_sqlalchemy_engine

# As we are using the lava connection manager, we just need the connection ID
# this time – not the connector script. So use LAVA_CONNID_DB not LAVA_CONN_DB.

conn_id = os.environ['LAVA_CONNID_DB']
realm = os.environ['LAVA_REALM']

engine = get_sqlalchemy_engine(conn_id, realm)
# engine is a standard SQLAlchemy engine.

with engine.connect() as conn:
    for row in conn.execute('... an SQL query ...'):
        print(row)

# Or use with pandas
table_df = pd.read_sql_table('my_table', con=engine)
```

!!! note
    There is a known issue for SQLAlchemy and pg8000. See the
    [workaround](#pg8000-type-error-with-sqlalchemy).

## Database Connections - The Good, the Bad and the Ugly of DBAPI 2.0

!!! note ""
    Aaaah–aaaah–aaah–aaaah… Wah–wah–wahhhh…

    (Don't tell me you don't know)

Lava uses DBAPI 2.0 based database drivers, the interface for which is specified
in [PEP 249](https://www.python.org/dev/peps/pep-0249/).

### The Good

DBAPI 2.0 provides some level of interface consistency across database types. In
simple cases, you only need to invoke the lava `get_pysql_connection()` function
as described above to obtain a database connection which can be used to execute
queries in a more or less consistent way across database types. But ...

### The Ugly

While DBAPI 2.0 provides `Connection.commit()` and `Connection.rollback()`
functions, it does not provide a `Connection.begin()` function to start a
transaction and driver implementations can differ in how they handle this.
(Most, but not all, handle this by setting `Connection.autocommit`). Different
databases also use different SQL syntax to begin a transaction. Oracle is
notable in that it does not support `BEGIN TRANSACTION` in the way that Postgres
and MySQL do.

To avoid this problem, lava provides a helper function
[lava.lib.db.begin_transaction()][lava.lib.db.begin_transaction].
```python
from lava.connection import get_pysql_connection
from lava.lib.db import begin_transaction

conn = get_pysql_connection(...)
cursor = conn.cursor()

try:
    begin_transaction(conn, cursor)
    # Do some SQL stuff
except Exception:
    conn.rollback()
else:
    conn.commit()
finally:
    conn.close()
```

### The Bad

[PEP 249](https://www.python.org/dev/peps/pep-0249/) defines 5 different
possible mechanisms for passing query parameters when a query is executed.

This is because it is absolutely critical for a *standard* to have 5
incompatible ways of doing exactly the same thing.

Unfortunately there is no consistency across different drivers as to which
subset of these is implemented or the default setting. The `paramstyle` module
constant will specify the default mechanism.

Some drivers, such as pg8000, allow the `paramstyle` *constant* to be set to
different values to support different parameter passing styles. Some don't.

It's a bit of a mess unfortunately and makes writing driver independent code
inordinately difficult. You either need to test the module's `paramstyle`
setting and adapt the parameter passing mechanism at run-time or just make do
with the specific driver settings.

## DBAPI 2.0 Usage in Lava

Lava uses the following drivers by default. Check the documentation for the
driver for more details.

|Database Family|Driver|
|-|-|
|MSSQL|[pyodbc](https://pypi.org/project/pyodbc/)|
|MySQL|[PyMySQL](https://pymysql.readthedocs.io/en/latest/)|
|Oracle|[cx\_Oracle](https://oracle.github.io/python-cx_Oracle/)|
|Postgres|[pg8000](https://github.com/tlocke/pg8000)|
|Redshift|[pg8000](https://github.com/tlocke/pg8000)|
|SQLite3|[sqlite3](https://docs.python.org/3/library/sqlite3.html)|

Python code either must be sophisticated enough to adapt to the DBAPI 2.0
variations at run-time or must have specific knowledge of which driver is being
used. Using [SQLAlchemy](#connection-handling-for-sqlalchemy)
instead of the native interface may be of assistance in the former option.

Lava also provides limited support to select an alternate driver for some
database types. This is done using the `subtype` field in the database
connection specification. Refer to individual connectors for details.
