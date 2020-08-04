#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import PIL
from resizeimage import resizeimage

from . import save_image
from ..constants import ALPHA_NOT_SUPPORTED


def resize_image(
    fpath, width, height=None, to=None, method="width", allow_upscaling=True, **params,
):
    """ resize an image file (dimensions)

        methods: width, height, cover
        allow upscaling: upscale image preserving aspect ratio if required before resizing """
    with PIL.Image.open(fpath) as image:
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
    # save the image
    save_image(resized, str(to) if to is not None else fpath, image_format, **params)
