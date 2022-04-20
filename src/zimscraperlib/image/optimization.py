#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu


""" An image optimization module to optimize the following image formats:

    - JPEG (using optimize-images)
    - PNG (using optimize-images)
    - GIF (using gifsicle with lossy optimization)
    - WebP (using Pillow)

    Some important notes:
    - This makes use of the --lossy option from gifsicle which is present
     only in versions above 1.92.
      If the package manager has a lower version, you can build gifsicle
      from source and install or
      do not use the lossiness option.

    - Presets for the optimizer are available in zimscraperlib.image.presets.

    - If no options for an image optimization is passed, the optimizer
    can still run on default settings which give
      a bit less size than the original images but maintain a high quality. """


import io
import os
import pathlib
import subprocess
from typing import Optional, Tuple, Union

import piexif
from optimize_images.img_aux_processing import do_reduce_colors, rebuild_palette
from optimize_images.img_aux_processing import remove_transparency as remove_alpha
from optimize_images.img_dynamic_quality import jpeg_dynamic_quality
from PIL import Image

from .convertion import convert_image
from .probing import format_for
from .utils import save_image


def ensure_matches(
    src: pathlib.Path,
    fmt: str,
) -> None:
    """Raise ValueError if src is not of image type `fmt`"""

    if format_for(src, from_suffix=False) != fmt:
        raise ValueError(f"{src} is not of format {fmt}")


def optimize_png(
    src: Union[pathlib.Path, io.BytesIO],
    dst: Optional[pathlib.Path] = None,
    reduce_colors: Optional[bool] = False,
    max_colors: Optional[int] = 256,
    fast_mode: Optional[bool] = True,
    remove_transparency: Optional[bool] = False,
    background_color: Optional[Tuple[int, int, int]] = (255, 255, 255),
    **options,
) -> Union[pathlib.Path, io.BytesIO]:

    """method to optimize PNG files using a pure python external optimizer

    Arguments:
        reduce_colors: Whether to reduce colors using adaptive color pallette (boolean)
            values: True | False
        max_colors: Maximum number of colors
        if reduce_colors is True (integer between 1 and 256)
            values: 35 | 64 | 256 | 128 | XX
        fast_mode: Whether to use faster but weaker compression (boolean)
            values: True | False
        remove_transparency: Whether to remove transparency (boolean)
            values: True | False
        background_color: Background color
        if remove_transparency is True (tuple containing RGB values)
            values: (255, 255, 255) | (221, 121, 108) | (XX, YY, ZZ)"""

    ensure_matches(src, "PNG")

    img = Image.open(src)

    if remove_transparency:
        img = remove_alpha(img, background_color)

    if reduce_colors:
        img, _, _ = do_reduce_colors(img, max_colors)

    if not fast_mode and img.mode == "P":
        img, _ = rebuild_palette(img)

    if dst is None:
        dst = io.BytesIO()
    img.save(dst, optimize=True, format="PNG")
    if isinstance(dst, io.BytesIO):
        dst.seek(0)
    return dst


def optimize_jpeg(
    src: Union[pathlib.Path, io.BytesIO],
    dst: Optional[pathlib.Path] = None,
    quality: Optional[int] = 85,
    fast_mode: Optional[bool] = True,
    keep_exif: Optional[bool] = True,
    **options,
) -> Union[pathlib.Path, io.BytesIO]:

    """method to optimize JPEG files using a pure python external optimizer
    quality: JPEG quality (integer between 1 and 100)
        values: 50 | 55 | 35 | 100 | XX
    keep_exif: Whether to keep EXIF data in JPEG (boolean)
        values: True | False
    fast_mode: Use the supplied quality value. If turned off, optimizer will
               get dynamic quality value to ensure better compression
        values: True | False"""

    ensure_matches(src, "JPEG")

    img = Image.open(src)
    orig_size = (
        os.path.getsize(src)
        if isinstance(src, pathlib.Path)
        else src.getbuffer().nbytes
    )

    had_exif = False
    if (isinstance(src, io.BytesIO) and piexif.load(src.getvalue())["Exif"]) or (
        isinstance(src, pathlib.Path) and piexif.load(str(src))["Exif"]
    ):
        had_exif = True

    # only use progressive if file size is bigger
    use_progressive_jpg = orig_size > 10240  # 10KiB

    if fast_mode:
        quality_setting = quality
    else:
        quality_setting, _ = jpeg_dynamic_quality(img)

    if dst is None:
        dst = io.BytesIO()

    img.save(
        dst,
        quality=quality_setting,
        optimize=True,
        progressive=use_progressive_jpg,
        format="JPEG",
    )

    if isinstance(dst, io.BytesIO):
        dst.seek(0)

    if keep_exif and had_exif:

        piexif.transplant(
            exif_src=str(src.resolve())
            if isinstance(src, pathlib.Path)
            else src.getvalue(),
            image=str(dst.resolve())
            if isinstance(dst, pathlib.Path)
            else dst.getvalue(),
            new_file=dst,
        )

    return dst


def optimize_webp(
    src: Union[pathlib.Path, io.BytesIO],
    dst: Optional[pathlib.Path] = None,
    lossless: Optional[bool] = False,
    quality: Optional[int] = 60,
    method: Optional[int] = 6,
    **options,
) -> Union[pathlib.Path, io.BytesIO]:
    """method to optimize WebP using Pillow options
    lossless: Whether to use lossless compression (boolean)
        values: True | False
    quality: WebP quality for lossy, effort put into compression
    for lossless (integer between 0 to 100)
        values: 30 | 45 | 100 | XX
    method: Quality/speed trade-off;
    higher values give better compression (integer between 1 and 6)
        values: 1 | 2 | 3 | 4 | 5 | 6

    refer to the link for more details
    https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#webp"""

    ensure_matches(src, "WEBP")
    params = {
        "lossless": lossless,
        "quality": quality,
        "method": method,
    }

    webp_image = Image.open(src)
    if dst is None:
        dst = io.BytesIO()
        webp_image.save(dst, format="WEBP", **params)
        dst.seek(0)
    else:
        try:
            save_image(webp_image, dst, fmt="WEBP", **params)
        except Exception as exc:
            if src.resolve() != dst.resolve() and dst.exists():
                dst.unlink()  # pragma: nocover
            raise exc
    return dst


def optimize_gif(
    src: pathlib.Path,
    dst: pathlib.Path,
    optimize_level: Optional[int] = 1,
    lossiness: Optional[int] = None,
    interlace: Optional[bool] = True,
    no_extensions: Optional[bool] = True,
    max_colors: Optional[int] = None,
    **options,
) -> pathlib.Path:
    """method to optimize GIFs using gifsicle >= 1.92
    optimize_level: Optimization level;
    higher values give better compression (integer between 1 and 3)
        values: 1 | 2 | 3
    lossiness: Level of lossy optimization to use;
    higher values give better compression (integer)
        values: 20 | 45 | 80 | XX
    interlace: Whether to interlace the frames (boolean)
        values: True | False
    no_extensions: Whether to remove all extension options from GIF (boolean)
        values: True | False
    max_colors: Maximum number of colors in resultant GIF (integer between 2 and 256)
        values: 2 | 86 | 128 | 256 | XX

    refer to the link for more details - https://www.lcdf.org/gifsicle/man.html"""

    ensure_matches(src, "GIF")

    # use gifsicle
    args = ["gifsicle"]
    if optimize_level:
        args += [f"-O{optimize_level}"]
    if max_colors:
        args += ["--colors", str(max_colors)]
    if lossiness:
        args += [f"--lossy={lossiness}"]
    if no_extensions:
        args += ["--no-extensions"]
    if interlace:
        args += ["--interlace"]
    args += [str(src)]
    with open(dst, "w") as out_file:
        gifsicle = subprocess.run(args, stdout=out_file)

    # remove dst if gifsicle failed and src is different from dst
    if gifsicle.returncode != 0 and src.resolve() != dst.resolve() and dst.exists():
        dst.unlink()  # pragma: nocover

    # raise error if unsuccessful
    gifsicle.check_returncode()
    return dst


def optimize_image(
    src: pathlib.Path,
    dst: pathlib.Path,
    delete_src: Optional[bool] = False,
    convert: Optional[Union[bool, str]] = False,
    **options,
) -> bool:
    """Optimize image, automatically selecting correct optimizer

    delete_src: whether to remove src file upon success (boolean)
        values: True | False
    convert: whether/how to convert from source before optimizing (str or boolean)
        values: False: don't convert
                True: convert to format implied by dst suffix
                "FMT": convert to format FMT (use Pillow names)"""

    src_format, dst_format = format_for(src, from_suffix=False), format_for(dst)
    # if requested, convert src to requested format into dst path
    if convert and src_format != dst_format:
        src_format = dst_format = convert if isinstance(convert, str) else dst_format
        convert_image(src, dst, fmt=src_format)
        src_img = pathlib.Path(dst)
    else:
        src_img = pathlib.Path(src)

    {
        "JPEG": optimize_jpeg,
        "PNG": optimize_png,
        "GIF": optimize_gif,
        "WEBP": optimize_webp,
    }.get(src_format)(src_img, dst, **options)

    # delete src image if requested
    if delete_src and src.exists() and src.resolve() != dst.resolve():
        src.unlink()
