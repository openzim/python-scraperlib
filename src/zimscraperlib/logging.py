#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import sys
import logging
from logging.handlers import RotatingFileHandler

DEFAULT_FORMAT = "[%(asctime)s] %(levelname)s:%(message)s"


def getLogger(
    name,
    level=logging.INFO,
    console=sys.stdout,
    log_format=DEFAULT_FORMAT,
    file=False,
    file_level=None,
    file_format=None,
    file_max=2 ** 20,
    file_nb_backup=1,
):
    """ configured logger for most usages

        - name: name of your logger
        - level: console level
        - log_format: format string
        - console: False | True (sys.stdout) | sys.stdout | sys.stderr
        - file: False | pathlib.Path
        - file_level: log level for file or console_level
        - file_format: format string for file or log_format """
    logger = logging.Logger(name)
    logger.setLevel(logging.DEBUG)

    # setup console logging
    if console:
        console_handler = logging.StreamHandler(console)
        console_handler.setFormatter(logging.Formatter(log_format))
        console_handler.setLevel(level)
        logger.addHandler(console_handler)

    if file:
        file_handler = RotatingFileHandler(
            file, maxBytes=file_max, backupCount=file_nb_backup
        )
        file_handler.setFormatter(logging.Formatter(file_format or log_format))
        file_handler.setLevel(file_level or level)
        logger.addHandler(file_handler)

    return logger


def nicer_args_join(args):
    """ slightly better concateated list of subprocess args for display """
    nargs = args[0:1]
    for arg in args[1:]:
        nargs.append(arg if arg.startswith("-") else '"{}"'.format(arg))
    return " ".join(nargs)
