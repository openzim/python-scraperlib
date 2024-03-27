#!/usr/bin/env python3
# vim: ai ts=4 sts=4 et sw=4 nu

from __future__ import annotations

import io
import pathlib

import PIL
from resizeimage import resizeimage

from zimscraperlib.constants import ALPHA_NOT_SUPPORTED
from zimscraperlib.image.utils import save_image


def resize_image(
    src: pathlib.Path | io.BytesIO,
    width: int,
    height: int | None = None,
    dst: pathlib.Path | io.BytesIO | None = None,
    method: str | None = "width",
    allow_upscaling: bool | None = True,  # noqa: FBT002
    **params: str,
) -> None:
    """resize an image to requested dimensions

    methods: width, height, cover, thumbnail
    allow upscaling: upscale image first, preserving aspect ratio if required"""
    with PIL.Image.open(src) as image:  # pyright: ignore
        # preserve image format as resize() does not transmit it into new object
        image_format = image.format
        image_mode = image.mode

        # upscale if required preserving the aspect ratio
        if allow_upscaling:
            height_width_ratio = float(image.size[1]) / float(image.size[0])
            if image.size[0] < width:
                image = image.resize(  # noqa: PLW2901
                    (width, int(width * height_width_ratio))
                )
            if height and image.size[1] < height:
                image = image.resize(  # noqa: PLW2901
                    (int(height / height_width_ratio), height)
                )

        # resize using the requested method
        if method == "width":
            resized = resizeimage.resize(method, image, width)
        elif method == "height":
            resized = resizeimage.resize(method, image, height)
        else:
            resized = resizeimage.resize(method, image, [width, height])

    # remove alpha layer if not supported and added during resizing
    if resized.mode == "RGBA" and image_format in ALPHA_NOT_SUPPORTED:
        resized = resized.convert(image_mode)

    # reset src if it's a byte stream and should be resized in-place
    if dst is None and isinstance(src, io.BytesIO):
        src.seek(0)

    save_image(
        resized,
        dst if dst is not None else src,  # pyright: ignore
        image_format,
        **params,
    )
