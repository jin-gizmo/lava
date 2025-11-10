"""Argparse utilities."""

import argparse

__author__ = 'Murray Andrews'


# ------------------------------------------------------------------------------
class StoreNameValuePair(argparse.Action):
    """
    Used with argparse to store values from options of the form ``--option name=value``.

    The destination (self.dest) will be created as a dict {name: value}. This
    allows multiple name-value pairs to be set for the same option.

    Usage is:

    ```python
    argparser.add_argument('-x', metavar='key=value', action=StoreNameValuePair)
    ```

    ... or ...

    ```python
    argparser.add_argument(
        '-x', metavar='key=value ...', action=StoreNameValuePair, nargs='+'
    )
    ```

    """

    # --------------------------------------------------------------------------
    # noinspection PyUnresolvedReferences
    def __call__(self, parser, namespace, values, option_string=None):
        """Handle name=value option."""

        if not hasattr(namespace, self.dest) or not getattr(namespace, self.dest):
            setattr(namespace, self.dest, {})
        argdict = getattr(namespace, self.dest)

        if not isinstance(values, list):
            values = [values]
        for val in values:
            try:
                n, v = val.split('=', 1)
            except ValueError as e:
                raise argparse.ArgumentError(self, str(e))
            argdict[n] = v


# ------------------------------------------------------------------------------
class ArgparserExitError(Exception):
    """When a premature exit from argparse is suppressed."""

    pass


# Backward compatibility only
ArgparserExitException = ArgparserExitError


class ArgparserNoExit(argparse.ArgumentParser):
    """Argparse that throws exception on bad arg instead of exiting."""

    def exit(self, status=0, message=None):  # noqa A003
        """Stop argparse from exiting on bad options."""

        print(message)
        if status:
            raise ArgparserExitError(message)
