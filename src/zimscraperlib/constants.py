#!/usr/bin/env python3
# vim: ai ts=4 sts=4 et sw=4 nu

import pathlib

from zimscraperlib.__about__ import __version__

ROOT_DIR = pathlib.Path(__file__).parent
NAME = pathlib.Path(__file__).parent.name
SCRAPER = f"{NAME} {__version__}"
CONTACT = "dev@openzim.org"
DEFAULT_USER_AGENT = f"{NAME}/{__version__} ({CONTACT})"

UTF8 = "UTF-8"

# list of Image formats witout Alpha Channel support
ALPHA_NOT_SUPPORTED = ["JPEG", "BMP", "EPS", "PCX"]

# list of mimetypes we consider articles using it should default to FRONT_ARTICLE
FRONT_ARTICLE_MIMETYPES = ["text/html"]

RECOMMENDED_MAX_TITLE_LENGTH = 30
MAXIMUM_DESCRIPTION_METADATA_LENGTH = 80
MAXIMUM_LONG_DESCRIPTION_METADATA_LENGTH = 4000
