#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu


""" An image optimization module to optimize the following image formats:

    - JPEG (using optimize-images)
    - PNG (using optimize-images)
    - GIF (using gifsicle with lossy optimization)
    - WebP (using Pillow)

    Some important notes:
    - This makes use of the --lossy option from gifsicle which is present only in versions above 1.92.
      If the package manager has a lower version, you can build gifsicle from source and install or
      do not use the lossiness option.

    - Presets for the optimizer are available in zimscraperlib.image.presets.

    - If no options for an image optimization is passed, the optimizer can still run on default settings which give
      a bit less size than the original images but maintain a high quality. """


import pathlib
import shutil
import subprocess
import tempfile
from typing import Optional, Tuple, Union

from optimize_images.data_structures import Task
from optimize_images.do_optimization import do_optimization
from PIL import Image

from . import save_image
from .convertion import convert_image
from .probing import format_for


def get_temporary_copy(src: pathlib.Path) -> pathlib.Path:
    tmp_fh = tempfile.NamedTemporaryFile(delete=False, suffix=src.suffix)
    tmp_fh.close()
    tmp_path = pathlib.Path(tmp_fh.name)
    shutil.copy(src, tmp_path)
    return tmp_path


def run_optimize_images_task(
    optimization_task: Task, tmp_path: pathlib.Path, dst: pathlib.Path
) -> bool:
    def cleanup(tmp: pathlib.Path) -> None:
        if tmp.exists():
            tmp.unlink()

    try:
        result = do_optimization(optimization_task)
        if result.was_optimized:
            shutil.move(tmp_path, dst)
    except Exception as exc:
        cleanup(tmp_path)
        cleanup(dst)
        raise exc

    cleanup(tmp_path)
    return result.was_optimized


def ensure_matches(
    src: pathlib.Path,
    fmt: str,
) -> None:
    """ Raise ValueError if src is not of image type `fmt` """

    if format_for(src) != fmt:
        raise ValueError(f"{src} is not of format {fmt}")


def optimize_png(
    src: pathlib.Path,
    dst: pathlib.Path,
    reduce_colors: Optional[bool] = False,
    max_colors: Optional[int] = 256,
    fast_mode: Optional[bool] = True,
    remove_transparency: Optional[bool] = False,
    background_color: Optional[Tuple[int, int, int]] = (255, 255, 255),
    grayscale: Optional[bool] = False,
    **options,
) -> bool:

    """method to optimize PNG files using a pure python external optimizer

    Arguments:
        reduce_colors: Whether to reduce colors using adaptive color pallette (boolean)
            values: True | False
        max_colors: Maximum number of colors if reduce_colors is True (integer between 1 and 256)
            values: 35 | 64 | 256 | 128 | XX
        fast_mode: Whether to use faster but weaker compression (boolean)
            values: True | False
        remove_transparency: Whether to remove transparency (boolean)
            values: True | False
        background_color: Background color if remove_transparency is True (tuple containing RGB values)
            values: (255, 255, 255) | (221, 121, 108) | (XX, YY, ZZ)
        grayscale: Whether to convert image to grayscale (boolean)
            values: True | False"""

    ensure_matches(src, "PNG")

    # use a temporary file as source as optimization is done destructively
    tmp_path = get_temporary_copy(src)

    # generate PNG task for optimize_images

    optimization_task = Task(
        src_path=str(tmp_path.resolve()),
        # quality is specific to JPEG and hence is ignored, but we need to supply the default value
        quality=90,
        remove_transparency=remove_transparency,
        reduce_colors=reduce_colors,
        # max_colors is ignored if reduce_colors is False, but we need to provide a default value
        max_colors=max_colors,
        # max_w and max_h is 0 because we have a better image resizing function in scraperlib already
        max_w=0,
        max_h=0,
        # keep_exif is specific to JPEG and hence is ignored, but we need to supply the default value
        keep_exif=False,
        # convert_all converts all PNG to JPEG, hence set to False
        convert_all=False,
        # conv_big converts big PNG images to JPEG, hence set to False
        conv_big=False,
        # force_del deletes the original PNG after convertion to JPEG if the above two options are used, hence kept False
        force_del=False,
        # bg_color is only used if remove_transparency is True, but we need to supply a default value always
        bg_color=background_color,
        grayscale=grayscale,
        no_size_comparison=True,
        fast_mode=fast_mode,
    )

    # optimize the image
    return run_optimize_images_task(optimization_task, tmp_path, dst)


def optimize_jpeg(
    src: pathlib.Path,
    dst: pathlib.Path,
    quality: Optional[int] = 85,
    fast_mode: Optional[bool] = True,
    keep_exif: Optional[bool] = True,
    grayscale: Optional[bool] = False,
    **options,
) -> bool:

    """method to optimize JPEG files using a pure python external optimizer
    quality: JPEG quality (integer between 1 and 100)
        values: 50 | 55 | 35 | 100 | XX
    keep_exif: Whether to keep EXIF data in JPEG (boolean)
        values: True | False
    grayscale: Whether to convert image to grayscale (boolean)
        values: True | False
    fast_mode: Whether to use faster but weaker compression (boolean)
        values: True | False"""

    ensure_matches(src, "JPEG")

    # use a temporary file as source as optimization is done destructively
    tmp_path = get_temporary_copy(src)

    # generate JPEG task for optimize_images

    optimization_task = Task(
        src_path=str(tmp_path.resolve()),
        quality=quality,
        # remove_transparency is specific to PNG and hence is ignored, but we need to supply the default value
        remove_transparency=False,
        # reduce_colors is specific to PNG and hence is ignored, but we need to supply the default value
        reduce_colors=False,
        # max_colors is specific to PNG and hence is ignored, but we need to supply the default value
        max_colors=256,
        # max_w and max_h is 0 because we have a better image resizing function in scraperlib already
        max_w=0,
        max_h=0,
        keep_exif=keep_exif,
        # convert_all is specific to PNG and hence is ignored, but we need to supply the default value
        convert_all=False,
        # convert_big is specific to PNG and hence is ignored, but we need to supply the default value
        conv_big=False,
        # force_del is specific to PNG and hence is ignored, but we need to supply the default value
        force_del=False,
        # bg_color is specific to PNG and hence is ignored, but we need to supply the default value
        bg_color=(255, 255, 255),
        grayscale=grayscale,
        no_size_comparison=True,
        fast_mode=fast_mode,
    )

    # optimize the image
    return run_optimize_images_task(optimization_task, tmp_path, dst)


def optimize_webp(
    src: pathlib.Path,
    dst: pathlib.Path,
    lossless: Optional[bool] = False,
    quality: Optional[int] = 60,
    method: Optional[int] = 6,
    **options,
) -> bool:
    """method to optimize WebP using Pillow options
    lossless: Whether to use lossless compression (boolean)
        values: True | False
    quality: WebP quality for lossy, effort put into compression for lossless (integer between 0 to 100)
        values: 30 | 45 | 100 | XX
    method: Quality/speed trade-off; higher values give better compression (integer between 1 and 6)
        values: 1 | 2 | 3 | 4 | 5 | 6

    refer to the link for more details - https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#webp"""

    ensure_matches(src, "WEBP")
    params = {
        "lossless": lossless,
        "quality": quality,
        "method": method,
    }

    try:
        webp_image = Image.open(src)
        save_image(webp_image, dst, fmt="WEBP", **params)
    except Exception as exc:
        if src.resolve() != dst.resolve() and dst.exists():
            dst.unlink()
        raise exc
    return True


def optimize_gif(
    src: pathlib.Path,
    dst: pathlib.Path,
    optimize_level: Optional[int] = 1,
    lossiness: Optional[int] = None,
    interlace: Optional[bool] = True,
    no_extensions: Optional[bool] = True,
    max_colors: Optional[int] = None,
    **options,
) -> bool:
    """method to optimize GIFs using gifsicle >= 1.92
    optimize_level: Optimization level; higher values give better compression (integer between 1 and 3)
        values: 1 | 2 | 3
    lossiness: Level of lossy optimization to use; higher values give better compression (integer)
        values: 20 | 45 | 80 | XX
    interlace: Whether to interlace the frames (boolean)
        values: True | False
    no_extensions: Whether to remove all extension options from GIF (boolean)
        values: True | False
    max_colors: Maximum number of colors in the resultant GIF (integer between 2 and 256)
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
        dst.unlink()

    # raise error if unsuccessful
    gifsicle.check_returncode()
    return True


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

    optimized = {
        "JPEG": optimize_jpeg,
        "PNG": optimize_png,
        "GIF": optimize_gif,
        "WEBP": optimize_webp,
    }.get(src_format)(src_img, dst, **options)

    # delete src image if requested
    if delete_src and optimized and src.exists() and src.resolve() != dst.resolve():
        src.unlink()

    return optimized
