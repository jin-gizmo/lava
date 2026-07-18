"""
Dummy DB API 2.0 module.

Typical usage would be:

```python
try:
    import pyodbc
except ImportError:
    from lava.lib.dbnone import dbapi_stub
    pyodbc = dbapi_stub('pyodbc')
```
"""

import types

__author__ = 'Murray Andrews'


# ------------------------------------------------------------------------------
def dbapi_stub(alias: str) -> types.ModuleType:
    """Create a stub DB API 2.0 module to stand-in for one that's not installed."""

    m = types.ModuleType(alias)
    # Some basic DBAPI 2 attributes ... just in case.
    m.apilevel = '2.0'
    m.threadsafety = 1
    m.paramstyle = 'qmark'
    m.alias = alias

    # noinspection PyUnusedLocal
    def connect(*args, **kwargs):
        """Stub the module connect function."""
        raise NotImplementedError(f'{alias}: Not installed or unsupported')

    class Connection:
        """Stub the Connection class."""

        def __init__(self, *args, **kwargs):
            raise NotImplementedError(f'{alias}: Not installed or unsupported')

    class Cursor:
        """Stub the Cursor class (probably redundant, but harmless)."""

        def __init__(self, *args, **kwargs):
            raise NotImplementedError(f'{alias}: Not installed or unsupported')

    m.connect = connect
    m.Connection = Connection
    m.Cursor = Cursor

    return m
