#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import shutil
import pathlib
import tempfile

from .constants import logger
from .download import save_file


def handle_user_provided_file(source=None, dest=None, in_dir=None, nocopy=False):
    """ downloads or copies a user provided file (URL or path)

        args:
            source: URL or path to a file (or None)
            dest:   pathlib.Path where to save the resulting file
                    using temp filename if None
            in_dir: pathlib.Path to gen dest within if specified
            nocopy: don't make a copy of source if a path was provided.
                    return source value instead
        return:
            pathlib.Path to handled file (or None)
        """
    if not source or not source.strip():
        return None

    if not dest:
        dest = pathlib.Path(
            tempfile.NamedTemporaryFile(
                suffix=pathlib.Path(source).suffix, dir=in_dir, delete=False
            ).name
        )

    if source.startswith("http"):
        logger.debug(f"download {source} -> {dest}")
        save_file(source, dest)
    else:
        source = pathlib.Path(source).expanduser().resolve()
        if not source.exists():
            raise IOError(f"{source} could not be found.")
        if nocopy:
            return source

        logger.debug(f"copy {source} -> {dest}")
        shutil.copy(source, dest)

    return dest
