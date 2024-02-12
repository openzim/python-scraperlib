#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 nu

import magic

from zimscraperlib.filesystem import (
    delete_callback,
    get_content_mimetype,
    get_file_mimetype,
)


def test_file_mimetype(png_image, jpg_image):
    assert get_file_mimetype(png_image) == "image/png"
    assert get_file_mimetype(jpg_image) == "image/jpeg"


def test_content_mimetype(png_image, jpg_image):
    with open(png_image, "rb") as fh:
        assert get_content_mimetype(fh.read(64)) == "image/png"

    with open(jpg_image, "rb") as fh:
        assert get_content_mimetype(fh.read(64)) == "image/jpeg"


def test_content_mimetype_fallback(monkeypatch, undecodable_byte_stream):
    # use raw function first to test actual code
    assert get_content_mimetype(undecodable_byte_stream) == "application/octet-stream"

    # mock then so we keep coverage on systems where magic works
    def raising_magic(*args, **kwargs):  # noqa: ARG001
        raise UnicodeDecodeError("nocodec", b"", 0, 1, "noreason")

    monkeypatch.setattr(magic, "from_buffer", raising_magic)
    assert get_content_mimetype(undecodable_byte_stream) == "application/octet-stream"


def test_mime_overrides(svg_image):
    mime_map = [(svg_image, "image/svg+xml")]
    for fpath, expected_mime in mime_map:
        assert get_file_mimetype(fpath) == expected_mime
        with open(fpath, "rb") as fh:
            assert get_content_mimetype(fh.read(64)) == expected_mime


def test_delete_callback_with_cb(tmp_path):
    class Store:
        called = 0

    def cb(*args):  # noqa: ARG001
        Store.called += 1

    fpath = tmp_path.joinpath("my-file")
    with open(fpath, "w") as fh:
        fh.write("content")

    delete_callback(fpath, cb, fpath.name)

    assert not fpath.exists()
    assert Store.called
    assert Store.called == 1


def test_delete_callback_without_cb(tmp_path):
    fpath = tmp_path.joinpath("my-file")
    with open(fpath, "w") as fh:
        fh.write("content")

    delete_callback(fpath)

    assert not fpath.exists()
