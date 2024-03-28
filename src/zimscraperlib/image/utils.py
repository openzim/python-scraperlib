#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 nu
from __future__ import annotations

import io
import pathlib

from PIL import Image


def save_image(
    src: Image,  # pyright: ignore
    dst: pathlib.Path | io.BytesIO,
    fmt: str | None = None,
    **params: str,
) -> None:
    """PIL.Image.save() wrapper setting default parameters"""
    args = {"JPEG": {"quality": 100}, "PNG": {}}.get(fmt, {})  # pyright: ignore
    args.update(params or {})
    src.save(dst, fmt, **args)  # pyright: ignore
