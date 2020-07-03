#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

from zimscraperlib.filesystem import get_file_mimetype, get_content_mimetype


def test_file_mimetype(png_image, jpg_image):
    assert get_file_mimetype(png_image) == "image/png"
    assert get_file_mimetype(jpg_image) == "image/jpeg"


def test_content_mimetype(png_image, jpg_image):
    with open(png_image, "rb") as fh:
        assert get_content_mimetype(fh.read(64)) == "image/png"

    with open(jpg_image, "rb") as fh:
        assert get_content_mimetype(fh.read(64)) == "image/jpeg"
