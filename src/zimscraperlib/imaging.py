#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import re
import colorsys

import PIL
import colorthief
from resizeimage import resizeimage


def get_colors(image_path, use_palette=True):
    """ (main, secondary) HTML color codes from an image path """

    def rgb_to_hex(r, g, b):
        """ hexadecimal HTML-friendly color code for RGB tuple """
        return "#{}{}{}".format(*[str(hex(x)[2:]).zfill(2) for x in (r, g, b)]).upper()

    def solarize(r, g, b):
        # calculate solarized color for main
        h, l, s = colorsys.rgb_to_hls(float(r) / 256, float(g) / 256, float(b) / 256)
        r2, g2, b2 = [int(x * 256) for x in colorsys.hls_to_rgb(h, 0.95, s)]
        return r2, g2, b2

    ct = colorthief.ColorThief(image_path)

    if use_palette:
        # extract two main colors from palette, solarizing second as background
        palette = ct.get_palette(color_count=2, quality=1)

        # using the first two colors of the palette?
        mr, mg, mb = palette[0]
        sr, sg, sb = solarize(*palette[1])
    else:
        # extract main color from image and solarize it as background
        mr, mg, mb = ct.get_color(quality=1)
        sr, sg, sb = solarize(mr, mg, mb)

    return rgb_to_hex(mr, mg, mb), rgb_to_hex(sr, sg, sb)


def resize_image(
    fpath, width, height=None, to=None, method="width", allow_upscaling=True
):
    """ resize an image file (dimensions)

        methods: width, height, cover
        allow upscaling: upscale image preserving aspect ratio if required before resizing """
    with open(str(fpath), "rb") as fp:
        image = PIL.Image.open(fp)
        # prserve image format
        image_format = image.format

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

    # save the image
    if resized.mode == "RGBA" and image_format == "JPEG":
        resized = resized.convert("RGB")
    kwargs = {"JPEG": {"quality": 100}, "PNG": {}}
    resized.save(
        str(to) if to is not None else fpath, image_format, **kwargs.get(image_format)
    )


def is_hex_color(text):
    """ whether supplied text is a valid hex-formated color code """
    return re.search(r"^#(?:[0-9a-fA-F]{3}){1,2}$", text)


def create_favicon(source_image, dest_ico):
    """ generate a squared favicon from a source image """
    if dest_ico.suffix != ".ico":
        raise ValueError("favicon extension must be ICO")

    img = PIL.Image.open(source_image)
    w, h = img.size
    # resize image to square first
    if w != h:
        size = min([w, h])
        resized = dest_ico.parent.joinpath(
            f"{source_image.stem}.tmp.{source_image.suffix}"
        )
        resize_image(source_image, size, size, resized, "contain")
        img = PIL.Image.open(resized)
    # now convert to ICO
    img.save(str(dest_ico))
