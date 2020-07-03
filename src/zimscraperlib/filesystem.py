#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

""" Files manipulation tools

    Shortcuts to retrieve mime type using magic
    """

import pathlib

import magic


def get_file_mimetype(fpath: pathlib.Path) -> str:
    """ MIME Type of file retrieved from magic headers """
    return magic.detect_from_filename(fpath).mime_type


def get_content_mimetype(content: bytes) -> str:
    """ MIME Type of content retrieved from magic headers """
    return magic.detect_from_content(content).mime_type
