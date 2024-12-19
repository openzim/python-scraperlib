import pathlib
from typing import Any

import magic
import pytest

from zimscraperlib.filesystem import (
    delete_callback,
    get_content_mimetype,
    get_file_mimetype,
)


def test_file_mimetype(png_image: pathlib.Path, jpg_image: pathlib.Path):
    assert get_file_mimetype(png_image) == "image/png"
    assert get_file_mimetype(jpg_image) == "image/jpeg"


def test_content_mimetype(png_image: pathlib.Path, jpg_image: pathlib.Path):
    with open(png_image, "rb") as fh:
        assert get_content_mimetype(fh.read(64)) == "image/png"

    with open(jpg_image, "rb") as fh:
        assert get_content_mimetype(fh.read(64)) == "image/jpeg"


def test_content_mimetype_fallback(
    monkeypatch: pytest.MonkeyPatch, undecodable_byte_stream: bytes
):
    # use raw function first to test actual code
    assert get_content_mimetype(undecodable_byte_stream) == "application/octet-stream"

    # mock then so we keep coverage on systems where magic works
    def raising_magic(*_: Any, **__: Any):
        raise UnicodeDecodeError("nocodec", b"", 0, 1, "noreason")

    monkeypatch.setattr(magic, "from_buffer", raising_magic)
    assert get_content_mimetype(undecodable_byte_stream) == "application/octet-stream"


def test_mime_overrides(svg_image: pathlib.Path):
    mime_map = [(svg_image, "image/svg+xml")]
    for fpath, expected_mime in mime_map:
        assert get_file_mimetype(fpath) == expected_mime
        with open(fpath, "rb") as fh:
            assert get_content_mimetype(fh.read(64)) == expected_mime


def test_delete_callback(tmp_path: pathlib.Path):
    fpath = tmp_path.joinpath("my-file")
    with open(fpath, "w") as fh:
        fh.write("content")

    delete_callback(fpath)

    assert not fpath.exists()
