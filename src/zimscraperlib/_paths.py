"""Dependency-free helpers shared by features with different extras."""

import pathlib
from contextlib import contextmanager
from tempfile import TemporaryDirectory
from typing import Any


@contextmanager
def path_from(path: pathlib.Path | TemporaryDirectory[Any] | str):
    """Context manager to get a Path from a path as string, Path or TemporaryDirectory

    Since scraperlib wants to manipulate only Path, scrapers might often needs this
    to create a path from what they have, especially since TemporaryDirectory context
    manager returns a string which is not really handy.
    """
    if isinstance(path, pathlib.Path):
        yield path
    elif isinstance(path, TemporaryDirectory):
        with path as pathname:
            yield pathlib.Path(pathname)
    else:
        yield pathlib.Path(path)
