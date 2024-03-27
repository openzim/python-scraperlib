#!/usr/bin/env python3
# vim: ai ts=4 sts=4 et sw=4 nu

from __future__ import annotations

import io
import logging
import pathlib
import sys
from collections.abc import Iterable
from logging.handlers import RotatingFileHandler

from zimscraperlib.constants import NAME

DEFAULT_FORMAT = "[%(name)s::%(asctime)s] %(levelname)s:%(message)s"
VERBOSE_DEPENDENCIES = ["urllib3", "PIL", "boto3", "botocore", "s3transfer"]


def getLogger(  # noqa: N802
    name: str,
    level: int | None = logging.INFO,
    console: io.TextIOBase | None = sys.stdout,  # pyright: ignore
    log_format: str | None = DEFAULT_FORMAT,
    file: pathlib.Path | None = False,  # noqa: FBT002  # pyright: ignore
    file_level: int | None = None,
    file_format: str | None = None,
    file_max: int | None = 2**20,
    file_nb_backup: int | None = 1,
    deps_level: int | None = logging.WARNING,  # noqa: ARG001
    additional_deps: Iterable | None = None,
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
    logging.Logger(NAME).setLevel(level)  # pyright: ignore

    # set arbitrary level for some known verbose dependencies
    # prevents them from polluting logs
    for logger_name in set(VERBOSE_DEPENDENCIES + additional_deps):  # pyright: ignore
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    logger = logging.Logger(name)
    logger.setLevel(logging.DEBUG)

    # setup console logging
    if console:
        console_handler = logging.StreamHandler(console)
        console_handler.setFormatter(logging.Formatter(log_format))
        console_handler.setLevel(level)  # pyright: ignore
        logger.addHandler(console_handler)

    if file:
        file_handler = RotatingFileHandler(  # pyright: ignore
            file,
            maxBytes=file_max,  # pyright: ignore
            backupCount=file_nb_backup,  # pyright: ignore
        )
        file_handler.setFormatter(logging.Formatter(file_format or log_format))
        file_handler.setLevel(file_level or level)  # pyright: ignore
        logger.addHandler(file_handler)

    return logger


def nicer_args_join(args: Iterable) -> str:
    """slightly better concateated list of subprocess args for display"""
    nargs = args[0:1]  # pyright: ignore
    for arg in args[1:]:  # pyright: ignore
        nargs.append(arg if arg.startswith("-") else f'"{arg}"')
    return " ".join(nargs)
