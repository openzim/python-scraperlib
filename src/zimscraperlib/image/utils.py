#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 nu
from __future__ import annotations

import io
import pathlib
from typing import IO, Any

from PIL.Image import Image
from PIL.ImageFile import ImageFile


def save_image(
    src: Image | ImageFile,
    dst: pathlib.Path | IO[bytes] | io.BytesIO,
    fmt: str,
    **params: Any,
) -> None:
    """PIL.Image.save() wrapper setting default parameters"""
    args = {"JPEG": {"quality": 100}, "PNG": {}}.get(fmt, {})
    args.update(params or {})
    src.save(dst, fmt, **args)
