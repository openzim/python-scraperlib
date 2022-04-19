#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import io
import logging
import pathlib
import sys
from logging.handlers import RotatingFileHandler
from typing import Iterable, Optional

from .constants import NAME

DEFAULT_FORMAT = "[%(name)s::%(asctime)s] %(levelname)s:%(message)s"
VERBOSE_DEPENDENCIES = ["urllib3", "PIL", "boto3", "botocore", "s3transfer"]


def getLogger(
    name: str,
    level: Optional[int] = logging.INFO,
    console: Optional[io.TextIOBase] = sys.stdout,
    log_format: Optional[str] = DEFAULT_FORMAT,
    file: Optional[pathlib.Path] = False,
    file_level: Optional[int] = None,
    file_format: Optional[str] = None,
    file_max: Optional[int] = 2**20,
    file_nb_backup: Optional[int] = 1,
    deps_level: Optional[int] = logging.WARNING,
    additional_deps: Optional[Iterable] = None,
):
    """configured logger for most usages

    - name: name of your logger
    - level: console level
    - log_format: format string
    - console: False | True (sys.stdout) | sys.stdout | sys.stderr
    - file: False | pathlib.Path
    - file_level: log level for file or console_level
    - file_format: format string for file or log_format
    - deps_level: log level for idendified verbose dependencies
    - additional_deps: additional modules names of verbose dependencies
        to assign deps_level to"""
    if additional_deps is None:
        additional_deps = []

    # align zimscraperlib logging level to that of scraper
    logging.Logger(NAME).setLevel(level)

    # set arbitrary level for some known verbose dependencies
    # prevents them from polluting logs
    for logger_name in set(VERBOSE_DEPENDENCIES + additional_deps):
        logging.getLogger(logger_name).setLevel(logging.WARNING)

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


def nicer_args_join(args: Iterable) -> str:
    """slightly better concateated list of subprocess args for display"""
    nargs = args[0:1]
    for arg in args[1:]:
        nargs.append(arg if arg.startswith("-") else '"{}"'.format(arg))
    return " ".join(nargs)
