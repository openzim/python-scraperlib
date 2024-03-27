#!/usr/bin/env python3
# vim: ai ts=4 sts=4 et sw=4 nu

from __future__ import annotations

import pathlib
import shutil
import tempfile

from zimscraperlib import logger
from zimscraperlib.constants import DEFAULT_USER_AGENT
from zimscraperlib.constants import (
    MAXIMUM_DESCRIPTION_METADATA_LENGTH as MAX_DESC_LENGTH,
)
from zimscraperlib.constants import (
    MAXIMUM_LONG_DESCRIPTION_METADATA_LENGTH as MAX_LONG_DESC_LENGTH,
)
from zimscraperlib.download import stream_file


def handle_user_provided_file(
    source: pathlib.Path | str | None = None,
    dest: pathlib.Path | None = None,
    in_dir: pathlib.Path | None = None,
    nocopy: bool = False,  # noqa: FBT001, FBT002
    user_agent: str | None = DEFAULT_USER_AGENT,
) -> pathlib.Path | None:
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
        headers = {"User-Agent": user_agent} if user_agent else None
        stream_file(url=str(source), fpath=dest, headers=headers)
    else:
        source = pathlib.Path(source).expanduser().resolve()
        if not source.exists():
            raise OSError(f"{source} could not be found.")
        if nocopy:
            return source

        logger.debug(f"copy {source} -> {dest}")
        shutil.copy(source, dest)

    return dest


def compute_descriptions(
    default_description: str,
    user_description: str | None,
    user_long_description: str | None,
) -> tuple[str, str | None]:
    """Computes short and long descriptions compliant with ZIM standard.

    Based on provided parameters, the function computes a short and a long description
    which are compliant with the ZIM standard (in terms of length).

    User description(s) are used if set. They are checked to not exceed ZIM standard
    maximum length ; an error is thrown otherwise ; if ok, they are returned.

    If user_description is not set, the description is computed based on the default
    description, truncated if needed.

    If user_long_description is not set and default description is too long for the
    description field, the long_description is computed based on the default description
    (truncated if needed), otherwise no long description is returned.

    args:
        default_description:   the description which will be used if user descriptions
                               are not set (typically fetched online)
        user_description:      the description set by the user (typically set by a
                               CLI argument)
        user_long_description: the long description set by the user (typically set by a
                               CLI argument)

    Returns a tuple of (description, long_description)
    """

    if user_description and len(user_description) > MAX_DESC_LENGTH:
        raise ValueError(
            f"Description too long ({len(user_description)}>{MAX_DESC_LENGTH})"
        )
    if user_long_description and len(user_long_description) > MAX_LONG_DESC_LENGTH:
        raise ValueError(
            f"LongDescription too long ({len(user_long_description)}"
            f">{MAX_LONG_DESC_LENGTH})"
        )

    if not user_long_description and len(default_description) > MAX_DESC_LENGTH:
        user_long_description = default_description[0:MAX_LONG_DESC_LENGTH]
        if len(default_description) > MAX_LONG_DESC_LENGTH:
            user_long_description = user_long_description[:-1] + "…"
    if not user_description:
        user_description = default_description[0:MAX_DESC_LENGTH]
        if len(default_description) > MAX_DESC_LENGTH:
            user_description = user_description[:-1] + "…"

    return (user_description, user_long_description)
