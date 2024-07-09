#!/usr/bin/env python3
# vim: ai ts=4 sts=4 et sw=4 nu

from __future__ import annotations

import pathlib
from typing import IO

from PIL.Image import open as pilopen

from zimscraperlib.constants import ALPHA_NOT_SUPPORTED
from zimscraperlib.image.probing import format_for
from zimscraperlib.image.transformation import resize_image
from zimscraperlib.image.utils import save_image


def convert_image(
    src: pathlib.Path | IO[bytes],
    dst: pathlib.Path | IO[bytes],
    **params: str,
) -> None:
    """convert an image file from one format to another
    params: Image.save() parameters. Depends on dest format.
    params can include the following keys:
     - fmt: specify the dest format (otherwise guessed from extension)
            ex: JPEG, PNG, BMP (and other PIL formats)
     - colorspace: convert to this colorspace. Otherwise not converted unless
     target format has no halpha channel while source had. In this case converted
     to RGB. ex: RGB, ARGB, CMYK (and other PIL colorspaces)"""

    colorspace = params.get("colorspace")  # requested colorspace
    fmt = params.pop("fmt").upper() if "fmt" in params else None  # requested format
    if not fmt:
        fmt = format_for(dst)
    with pilopen(src) as image:
        if image.mode == "RGBA" and fmt in ALPHA_NOT_SUPPORTED or colorspace:
            image = image.convert(colorspace or "RGB")  # noqa: PLW2901
        save_image(image, dst, fmt, **params)


def create_favicon(src: pathlib.Path, dst: pathlib.Path) -> None:
    """generate a squared favicon from a source image"""
    if dst.suffix != ".ico":
        raise ValueError("favicon extension must be ICO")

    img = pilopen(src)
    w, h = img.size
    # resize image to square first
    if w != h:
        size = min([w, h])
        resized = dst.parent.joinpath(f"{src.stem}.tmp.{src.suffix}")
        resize_image(src, size, size, resized, "contain")
        img = pilopen(resized)
    # now convert to ICO
    save_image(img, dst, "ICO")