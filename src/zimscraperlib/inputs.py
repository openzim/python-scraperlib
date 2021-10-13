#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import pathlib
import shutil
import tempfile
from typing import Optional, Union

from . import logger
from .download import stream_file


def handle_user_provided_file(
    source: Optional[Union[pathlib.Path, str]] = None,
    dest: Optional[pathlib.Path] = None,
    in_dir: pathlib.Path = None,
    nocopy: bool = False,
) -> Union[pathlib.Path, None]:
    """path to downloaded or copied a user provided file (URL or path)

    args:
        source: URL or path to a file (or None)
        dest:   pwhere to save the resulting file using temp filename if None
        in_dir: where to generate dest within if specified
        nocopy: don't make a copy of source if a path was provided.
                return source value instead"""
    if not source or not str(source).strip():
        return None

    if not dest:
        dest = pathlib.Path(
            tempfile.NamedTemporaryFile(
                suffix=pathlib.Path(source).suffix, dir=in_dir, delete=False
            ).name
        )

    if str(source).startswith("http"):
        logger.debug(f"download {source} -> {dest}")
        stream_file(url=str(source), fpath=dest)
    else:
        source = pathlib.Path(source).expanduser().resolve()
        if not source.exists():
            raise IOError(f"{source} could not be found.")
        if nocopy:
            return source

        logger.debug(f"copy {source} -> {dest}")
        shutil.copy(source, dest)

    return dest
