
# Known Issues

#### PG8000 type error with SQLAlchemy

PG8000 had a bug in its implementation that the SQLAlchemy driver patched over.
A recent pg8000 release introduced a patch for this issue that broke the SQLAlchemy
workaround.

See the [SQLAlchemy issue](https://github.com/sqlalchemy/sqlalchemy/issues/5645)
on GitHub.

The workaround is to change this:

```python
from lava.connection import get_sqlalchemy_engine

print('Connecting with sqlalchemy')
e = get_sqlalchemy_engine(conn_id, realm)

with e.connect() as conn:
    for row in conn.execute('SELECT whatever FROM wherever'):
        print(row)
```

to this:

```python
from lava.connection import get_sqlalchemy_engine

print('Connecting with sqlalchemy')
e = get_sqlalchemy_engine(conn_id, realm)

# This is the workaround
e.dialect.description_encoding = None

with e.connect() as conn:
    for row in conn.execute('SELECT whatever FROM wherever'):
        print(row)
```

The workaround is benign for other driver types.

If a code change is not possible, try switching from a pg8000 connector to a
PyGreSQL based connector. This should work fine without a code change.

#### Can't load plugin: sqlalchemy.dialects:postgresql.pygresql

SQLAlchemy support is currently not working with the PyGreSQL driver. Use PG8000
instead.
