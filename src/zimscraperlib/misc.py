"""Miscelaneous utils"""


def first[T](*args: T | None, default: T = "") -> T:
    """Return the first non-None value from *args; fallback to an empty string."""
    return next((item for item in args if item is not None), default)
