#!/usr/bin/env python3
# vim: ai ts=4 sts=4 et sw=4 nu

from __future__ import annotations

import colorsys
import io
import pathlib
import re

import colorthief
import PIL.Image


def get_colors(
    src: pathlib.Path, use_palette: bool | None = True  # noqa: FBT002
) -> tuple[str, str]:
    """(main, secondary) HTML color codes from an image path"""

    def rgb_to_hex(r: int, g: int, b: int) -> str:
        """hexadecimal HTML-friendly color code for RGB tuple"""
        return "#{}{}{}".format(*[str(hex(x)[2:]).zfill(2) for x in (r, g, b)]).upper()

    def solarize(r: int, g: int, b: int) -> tuple[int, int, int]:
        # calculate solarized color for main
        h, l, s = colorsys.rgb_to_hls(  # noqa: E741
            float(r) / 256, float(g) / 256, float(b) / 256
        )
        r2, g2, b2 = (int(x * 256) for x in colorsys.hls_to_rgb(h, 0.95, s))
        return r2, g2, b2

    ct = colorthief.ColorThief(src)

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


def is_hex_color(text: str) -> bool:
    """whether supplied text is a valid hex-formated color code"""
    return re.search(r"^#(?:[0-9a-fA-F]{3}){1,2}$", text)  # pyright: ignore


def format_for(
    src: pathlib.Path | io.BytesIO,
    from_suffix: bool = True,  # noqa: FBT001, FBT002
) -> str:
    """Pillow format of a given filename, either Pillow-detected or from suffix"""
    if not from_suffix:
        with PIL.Image.open(src) as img:
            return img.format  # pyright: ignore

    from PIL.Image import EXTENSION as ext_fmt_map  # noqa: N811
    from PIL.Image import init as init_pil

    init_pil()
    return ext_fmt_map[
        src.suffix  # pyright: ignore
    ]  # might raise KeyError on unknown extension


def is_valid_image(
    image: pathlib.Path | io.IOBase | bytes,
    imformat: str,
    size: tuple[int, int] | None = None,
) -> bool:
    """whether image is a valid imformat (PNG) image, optionnaly of requested size"""
    if isinstance(image, bytes):
        image = io.BytesIO(image)
    try:
        img = PIL.Image.open(image)
        if img.format != imformat:
            return False
        if size and img.size != size:
            return False
    except Exception:
        return False
    return True
