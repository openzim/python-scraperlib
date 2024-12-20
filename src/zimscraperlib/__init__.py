import logging as stdlogging
import os

from beartype.claw import beartype_this_package

beartype_this_package()

from zimscraperlib.constants import NAME
from zimscraperlib.logging import getLogger

debug = os.getenv("ZIMSCRAPERLIB_DEBUG")
logger = getLogger(NAME, level=stdlogging.DEBUG if debug else stdlogging.INFO)
