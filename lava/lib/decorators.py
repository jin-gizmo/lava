"""Function decorators."""

import inspect
import sys
from typing import Callable

__author__ = 'Murray Andrews'


# ------------------------------------------------------------------------------
def static_vars(**kwargs) -> Callable:
    """
    Allow a function to have static variables.

    Usage:

    ```python
    @static_vars(v1=10, v2={}, ...)
    def f(...):
        print(f.v1)
    ```

    :param kwargs:      Variable names and initial values.
    :return:            Decorated function.
    """

    def decorate(func):
        """Decorate a function to allow static vars."""
        for k in kwargs:
            setattr(func, k, kwargs[k])
        return func

    return decorate


# ------------------------------------------------------------------------------
def debug_func(func) -> Callable:
    """
    Print function call details.

    Details are - parameters names and effective values and return value.

    Usage:

    ```python
    @debug_func
    def f(...):
    ```

    """

    def wrapper(*args, **kwargs):
        """
        Wrap a function to print args and return value.

        :param args:        Postionals.
        :param kwargs:      Keywordss.
        :return:            Whatever the wrapped function returns.
        """

        func_args = inspect.signature(func).bind(*args, **kwargs).arguments
        func_args_str = ', '.join('{} = {!r}'.format(*item) for item in func_args.items())
        indent = ' ' * 2 * (len(inspect.stack()) - 1)
        print(f'{indent}--> {func.__module__}.{func.__qualname__} ( {func_args_str} )')
        ret_val = func(*args, **kwargs)
        print(f'{indent}<-- {func.__module__}.{func.__qualname__} | {ret_val}')
        return ret_val

    return wrapper


# ------------------------------------------------------------------------------
if sys.version_info >= (3, 13):
    from warnings import deprecated
else:
    import functools
    import warnings

    def deprecated(
        message: str, *, category: type[Warning] = DeprecationWarning, stacklevel: int = 1
    ) -> Callable:
        """Mark a function as deprecated."""

        def decorator(func):
            """Decorate the function with deprecation warning."""

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                """Wrap the function call with a deprecation warning."""
                warnings.warn(
                    f'{func.__name__} is deprecated. {message}',
                    category=category,
                    stacklevel=stacklevel + 1,
                )
                return func(*args, **kwargs)

            # Add the __deprecated__ attribute that griffe looks for
            wrapper.__deprecated__ = message
            return wrapper

        return decorator
