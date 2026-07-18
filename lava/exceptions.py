"""Lava exceptions."""

from __future__ import annotations

from typing import Any


# ------------------------------------------------------------------------------
class LavaError(Exception):
    """
    Lava specific exception.

    :param data:    Any JSON serialisable object.
    """

    def __init__(self, *args, data: Any = None, **kwargs):
        """Create a LavaError."""

        # noinspection PyArgumentList
        super().__init__(*args, **kwargs)
        self.data = data


# For backward compatibility ... for now
LavaException = LavaError
