""" Miscelaneous utils"""

from typing import Optional


def first(*args: Optional[object]) -> object:
    """first non-None value from *args ; fallback to empty string"""
    return next((item for item in args if item is not None), "")
