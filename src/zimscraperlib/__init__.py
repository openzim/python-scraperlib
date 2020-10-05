#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import logging as std_logging

from .constants import NAME
from .logging import getLogger

logger = getLogger(NAME, level=std_logging.DEBUG)
