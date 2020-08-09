#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

""" Files manipulation tools

    Shortcuts to retrieve mime type using magic
    """

import pathlib

import magic

# a mapping of various forms of the same mimetype to point to a single one
# this is necessary to deal with inconsistencies in the magic database on different platforms
MIME_MAP = {
    "image/svg": "image/svg+xml",
}


def get_file_mimetype(fpath: pathlib.Path) -> str:
    """ MIME Type of file retrieved from magic headers """

    detected_mime = magic.detect_from_filename(fpath).mime_type
    return MIME_MAP.get(detected_mime, detected_mime)


def get_content_mimetype(content: bytes) -> str:
    """ MIME Type of content retrieved from magic headers """

    detected_mime = magic.detect_from_content(content).mime_type
    return MIME_MAP.get(detected_mime, detected_mime)
