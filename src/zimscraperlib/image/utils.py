#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 nu

import pathlib
from typing import Optional

from PIL import Image


def save_image(
    src: Image,  # pyright: ignore
    dst: pathlib.Path,
    fmt: Optional[str] = None,
    **params: Optional[dict],
) -> None:
    """PIL.Image.save() wrapper setting default parameters"""
    args = {"JPEG": {"quality": 100}, "PNG": {}}.get(fmt, {})  # pyright: ignore
    args.update(params or {})
    src.save(dst, fmt, **args)  # pyright: ignore
