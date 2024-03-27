from __future__ import annotations

""" Miscelaneous utils"""


def first(*args: object | None) -> object:
    """first non-None value from *args ; fallback to empty string"""
    return next((item for item in args if item is not None), "")
