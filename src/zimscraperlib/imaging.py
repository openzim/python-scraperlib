#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import re
import colorsys

import PIL
import colorthief
from resizeimage import resizeimage


ALPHA_NOT_SUPPORTED = ["JPEG", "BMP", "EPS", "PCX"]


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


def save_image(image, dst, fmt, **params):
    """ saves an image with default args and overrides them if params are given
        params: PIL params (https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html) """
    args = {"JPEG": {"quality": 100}, "PNG": {}}.get(fmt, {})
    args.update(params or {})
    image.save(dst, fmt, **args)


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


def convert_image(src, dst, target_format, colorspace=None, **params):
    """ convert an image file from one format to another

        colorspace: RGB, ARGB, CMYK (and other PIL colorspaces)
        target_format: JPEG, PNG, BMP (and other PIL formats) """
    with PIL.Image.open(src) as image:
        dst_image = image
        if (
            image.mode == "RGBA" and target_format in ALPHA_NOT_SUPPORTED
        ) or colorspace:
            dst_image = (
                image.convert("RGB") if not colorspace else image.convert(colorspace)
            )
        save_image(dst_image, dst, target_format, **params)


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
