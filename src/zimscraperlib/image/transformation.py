#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import pathlib
from typing import Optional

import PIL
from resizeimage import resizeimage

from .utils import save_image
from ..constants import ALPHA_NOT_SUPPORTED


def resize_image(
    src: pathlib.Path,
    width: int,
    height: Optional[int] = None,
    dst: Optional[pathlib.Path] = None,
    method: Optional[str] = "width",
    allow_upscaling: Optional[bool] = True,
    **params: Optional[dict],
) -> None:
    """resize an image file to requested dimensions

    methods: width, height, cover
    allow upscaling: upscale image first, preserving aspect ratio if required"""
    with PIL.Image.open(src) as image:
        # preserve image format as resize() does not transmit it into new object
        image_format = image.format
        image_mode = image.mode

        # upscale if required preserving the aspect ratio
        if allow_upscaling:
            height_width_ratio = float(image.size[1]) / float(image.size[0])
            if image.size[0] < width:
                image = image.resize((width, int(width * height_width_ratio)))
            if height and image.size[1] < height:
                image = image.resize((int(height / height_width_ratio), height))

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

    save_image(resized, dst if dst is not None else src, image_format, **params)
