""" Files manipulation tools

    Shortcuts to retrieve mime type using magic"""

import pathlib
from contextlib import contextmanager
from tempfile import TemporaryDirectory
from typing import Any

import magic

# override some MIME-types found by libmagic to different ones
MIME_OVERRIDES = {
    "image/svg": "image/svg+xml",
}


def get_file_mimetype(fpath: pathlib.Path) -> str:
    """MIME Type of file retrieved from magic headers"""

    # detected_mime = magic.detect_from_filename(fpath).mime_type
    # return MIME_OVERRIDES.get(detected_mime, detected_mime)

    with open(fpath, "rb") as fh:
        return get_content_mimetype(fh.read(2048))


def get_content_mimetype(content: bytes | str) -> str:
    """MIME Type of content retrieved from magic headers"""

    try:
        detected_mime = magic.from_buffer(content, mime=True)
        if isinstance(
            detected_mime, bytes
        ):  # pragma: no cover (old python-magic versions where returning bytes)
            detected_mime = detected_mime.decode()
    except UnicodeDecodeError:
        return "application/octet-stream"
    return MIME_OVERRIDES.get(detected_mime, detected_mime)


def delete_callback(fpath: pathlib.Path):
    """helper deleting passed filepath"""
    fpath.unlink(missing_ok=True)


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
