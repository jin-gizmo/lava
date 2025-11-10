"""
Dummy DB API 2.0 module.

Typical usage would be:

```python
try:
    import db_module
except ImportError:
    import dbnone as db_module
    db_module.alias = 'db_module'
```

"""

__author__ = 'Murray Andrews'

# These do nothing ... just for compatibility
apilevel = '2.0'
threadsafety = 1
paramstyle = 'qmark'

alias = 'Unknown DBAPI 2.0 handler'


# ------------------------------------------------------------------------------
# noinspection PyUnusedLocal
def connect(*args, **kwargs):
    """
    Just throws an exception.

    :param args:        Ignored.
    :param kwargs:      Ignored.
    """

    raise NotImplementedError(f'{alias}: Not installed or unsupported')


# ------------------------------------------------------------------------------
class Connection:
    """
    A dummy connection class.

    Attempting to create an instance will result in an exception.

    :param args:        Ignored.
    :param kwargs:      Ignored.
    """

    def __init__(self, *args, **kwargs):
        """Create a dummy connection."""
        raise NotImplementedError(f'{alias}: Not installed or unsupported')


# ------------------------------------------------------------------------------
class Cursor:
    """
    A dummy Cursor class.

    Attempting to create an instance will result in an exception.

    :param args:        Ignored.
    :param kwargs:      Ignored.
    """

    def __init__(self, *args, **kwargs):
        """Not implemented."""
        raise NotImplementedError(f'{alias}: Not installed or unsupported')
