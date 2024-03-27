#!/usr/bin/env python3
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

from __future__ import annotations

import io
import os
import pathlib
import subprocess

import piexif
from optimize_images.img_aux_processing import do_reduce_colors, rebuild_palette
from optimize_images.img_aux_processing import remove_transparency as remove_alpha
from optimize_images.img_dynamic_quality import jpeg_dynamic_quality
from PIL import Image

from zimscraperlib.image.convertion import convert_image
from zimscraperlib.image.probing import format_for
from zimscraperlib.image.utils import save_image


def ensure_matches(
    src: pathlib.Path,
    fmt: str,
) -> None:
    """Raise ValueError if src is not of image type `fmt`"""

    if format_for(src, from_suffix=False) != fmt:
        raise ValueError(f"{src} is not of format {fmt}")


def optimize_png(
    src: pathlib.Path | io.BytesIO,
    dst: pathlib.Path | None = None,
    reduce_colors: bool | None = False,  # noqa: FBT002
    max_colors: int | None = 256,
    fast_mode: bool | None = True,  # noqa: FBT002
    remove_transparency: bool | None = False,  # noqa: FBT002
    background_color: tuple[int, int, int] | None = (255, 255, 255),
    **options,  # noqa: ARG001
) -> pathlib.Path | io.BytesIO:
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

    ensure_matches(src, "PNG")  # pyright: ignore

    img = Image.open(src)

    if remove_transparency:
        img = remove_alpha(img, background_color)  # pyright: ignore

    if reduce_colors:
        img, _, _ = do_reduce_colors(img, max_colors)  # pyright: ignore

    if not fast_mode and img.mode == "P":
        img, _ = rebuild_palette(img)

    if dst is None:
        dst = io.BytesIO()  # pyright: ignore
    img.save(dst, optimize=True, format="PNG")  # pyright: ignore
    if isinstance(dst, io.BytesIO):
        dst.seek(0)
    return dst  # pyright: ignore


def optimize_jpeg(
    src: pathlib.Path | io.BytesIO,
    dst: pathlib.Path | None = None,
    quality: int | None = 85,
    fast_mode: bool | None = True,  # noqa: FBT002
    keep_exif: bool | None = True,  # noqa: FBT002
    **options,  # noqa: ARG001
) -> pathlib.Path | io.BytesIO:
    """method to optimize JPEG files using a pure python external optimizer
    quality: JPEG quality (integer between 1 and 100)
        values: 50 | 55 | 35 | 100 | XX
    keep_exif: Whether to keep EXIF data in JPEG (boolean)
        values: True | False
    fast_mode: Use the supplied quality value. If turned off, optimizer will
               get dynamic quality value to ensure better compression
        values: True | False"""

    ensure_matches(src, "JPEG")  # pyright: ignore

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
    use_progressive_jpg = orig_size > 10240  # 10KiB  # noqa: PLR2004

    if fast_mode:
        quality_setting = quality
    else:
        quality_setting, _ = jpeg_dynamic_quality(img)

    if dst is None:
        dst = io.BytesIO()  # pyright: ignore

    img.save(
        dst,  # pyright: ignore
        quality=quality_setting,
        optimize=True,
        progressive=use_progressive_jpg,
        format="JPEG",
    )

    if isinstance(dst, io.BytesIO):
        dst.seek(0)

    if keep_exif and had_exif:
        piexif.transplant(
            exif_src=(
                str(src.resolve()) if isinstance(src, pathlib.Path) else src.getvalue()
            ),
            image=(
                str(dst.resolve())
                if isinstance(dst, pathlib.Path)
                else dst.getvalue()  # pyright: ignore
            ),
            new_file=dst,
        )

    return dst  # pyright: ignore


def optimize_webp(
    src: pathlib.Path | io.BytesIO,
    dst: pathlib.Path | None = None,
    lossless: bool | None = False,  # noqa: FBT002
    quality: int | None = 60,
    method: int | None = 6,
    **options,  # noqa: ARG001
) -> pathlib.Path | io.BytesIO:
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

    ensure_matches(src, "WEBP")  # pyright: ignore
    params = {
        "lossless": lossless,
        "quality": quality,
        "method": method,
    }

    webp_image = Image.open(src)
    if dst is None:
        dst = io.BytesIO()  # pyright: ignore
        webp_image.save(dst, format="WEBP", **params)  # pyright: ignore
        dst.seek(0)  # pyright: ignore
    else:
        try:
            save_image(webp_image, dst, fmt="WEBP", **params)  # pyright: ignore
        except Exception as exc:
            if src.resolve() != dst.resolve() and dst.exists():  # pyright: ignore
                dst.unlink()  # pragma: no cover
            raise exc
    return dst  # pyright: ignore


def optimize_gif(
    src: pathlib.Path,
    dst: pathlib.Path,
    optimize_level: int | None = 1,
    lossiness: int | None = None,
    interlace: bool | None = True,  # noqa: FBT002
    no_extensions: bool | None = True,  # noqa: FBT002
    max_colors: int | None = None,
    **options,  # noqa: ARG001
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
    args = ["/usr/bin/env", "gifsicle"]
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
        gifsicle = subprocess.run(args, stdout=out_file, check=False)

    # remove dst if gifsicle failed and src is different from dst
    if gifsicle.returncode != 0 and src.resolve() != dst.resolve() and dst.exists():
        dst.unlink()  # pragma: no cover

    # raise error if unsuccessful
    gifsicle.check_returncode()
    return dst


def optimize_image(
    src: pathlib.Path,
    dst: pathlib.Path,
    delete_src: bool | None = False,  # noqa: FBT002
    convert: bool | str | None = False,  # noqa: FBT002
    **options,
) -> bool:  # pyright: ignore
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
        convert_image(src, dst, fmt=src_format)  # pyright: ignore
        src_img = pathlib.Path(dst)
    else:
        src_img = pathlib.Path(src)

    {  # pyright: ignore
        "JPEG": optimize_jpeg,
        "PNG": optimize_png,
        "GIF": optimize_gif,
        "WEBP": optimize_webp,
    }.get(src_format)(src_img, dst, **options)

    # delete src image if requested
    if delete_src and src.exists() and src.resolve() != dst.resolve():
        src.unlink()
