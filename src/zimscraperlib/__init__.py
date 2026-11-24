import logging
import os

from beartype.claw import beartype_this_package

beartype_this_package()

from zimscraperlib.constants import NAME
from zimscraperlib.log_setup import getLogger

debug = os.getenv("ZIMSCRAPERLIB_DEBUG")
logger = getLogger(NAME, level=logging.DEBUG if debug else logging.INFO)
