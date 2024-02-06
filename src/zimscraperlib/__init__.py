#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 nu

import logging as stdlogging
import os

from zimscraperlib.constants import NAME
from zimscraperlib.logging import getLogger

debug = os.getenv("ZIMSCRAPERLIB_DEBUG")
logger = getLogger(NAME, level=stdlogging.DEBUG if debug else stdlogging.INFO)
