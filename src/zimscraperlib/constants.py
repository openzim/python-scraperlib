#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import pathlib

ROOT_DIR = pathlib.Path(__file__).parent
NAME = pathlib.Path(__file__).parent.name
with open(ROOT_DIR.joinpath("VERSION"), "r") as fh:
    VERSION = fh.read().strip()
SCRAPER = f"{NAME} {VERSION}"

UTF8 = "UTF-8"

# list of Image formats witout Alpha Channel support
ALPHA_NOT_SUPPORTED = ["JPEG", "BMP", "EPS", "PCX"]

# list of mimetypes we consider articles using it should default to FRONT_ARTICLE
FRONT_ARTICLE_MIMETYPES = ["text/html"]

# list of mandatory meta tags of the zim file.
ZIM_MANDATORY_METADATA_KEYS = [
    "name",
    "title",
    "creator",
    "publisher",
    "date",
    "description",
    "language",
]

# Default Value of Language
DEFAULT_LANG_ISO_639_1 = "en"
DEFAULT_LANG_ISO_639_3 = "eng"
