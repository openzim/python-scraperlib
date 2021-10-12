#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

from zimscraperlib.filesystem import (
    get_content_mimetype,
    get_file_mimetype,
    delete_callback,
)


def test_file_mimetype(png_image, jpg_image):
    assert get_file_mimetype(png_image) == "image/png"
    assert get_file_mimetype(jpg_image) == "image/jpeg"


def test_content_mimetype(png_image, jpg_image):
    with open(png_image, "rb") as fh:
        assert get_content_mimetype(fh.read(64)) == "image/png"

    with open(jpg_image, "rb") as fh:
        assert get_content_mimetype(fh.read(64)) == "image/jpeg"


def test_mime_overrides(svg_image):
    mime_map = [(svg_image, "image/svg+xml")]
    for fpath, expected_mime in mime_map:
        assert get_file_mimetype(fpath) == expected_mime
        with open(fpath, "rb") as fh:
            assert get_content_mimetype(fh.read(64)) == expected_mime


def test_delete_callback(tmp_path):
    class Store:
        called = 0

    def cb(*args):
        Store.called += 1

    fpath = tmp_path.joinpath("my-file")
    with open(fpath, "w") as fh:
        fh.write("content")

    delete_callback(fpath, cb, fpath.name)

    assert not fpath.exists()
    assert Store.called
    assert Store.called == 1
