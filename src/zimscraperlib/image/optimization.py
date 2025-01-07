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
from dataclasses import dataclass

import piexif  # pyright: ignore[reportMissingTypeStubs]
from optimize_images.img_aux_processing import (  # pyright: ignore[reportMissingTypeStubs]
    do_reduce_colors,
    rebuild_palette,
)
from optimize_images.img_aux_processing import (  # pyright: ignore[reportMissingTypeStubs]
    remove_transparency as remove_alpha,
)
from optimize_images.img_dynamic_quality import (  # pyright: ignore[reportMissingTypeStubs]
    jpeg_dynamic_quality,
)
from PIL import Image

from zimscraperlib.image.conversion import convert_image
from zimscraperlib.image.probing import format_for
from zimscraperlib.image.utils import save_image


def ensure_matches(
    src: pathlib.Path | io.BytesIO,
    fmt: str,
) -> None:
    """Raise ValueError if src is not of image type `fmt`"""

    if format_for(src, from_suffix=False) != fmt:
        raise ValueError(f"{src} is not of format {fmt}")


@dataclass
class OptimizePngOptions:
    """Dataclass holding PNG optimization options

    Arguments:
        reduce_colors: Whether to reduce colors using adaptive color pallette (boolean)
            values: True | False
        max_colors: Maximum number of colors if reduce_colors is True (integer between
            1 and 256)
            values: 35 | 64 | 256 | 128 | XX
        fast_mode: Whether to use faster but weaker compression (boolean)
            values: True | False
        remove_transparency: Whether to remove transparency (boolean)
            values: True | False
        background_color: Background color if remove_transparency is True (tuple
            containing RGB values)
            values: (255, 255, 255) | (221, 121, 108) | (XX, YY, ZZ)
    """

    max_colors: int = 256
    background_color: tuple[int, int, int] = (255, 255, 255)
    reduce_colors: bool | None = False
    fast_mode: bool | None = True
    remove_transparency: bool | None = False


def optimize_png(
    src: pathlib.Path | io.BytesIO,
    dst: pathlib.Path | io.BytesIO | None = None,
    options: OptimizePngOptions | None = None,
) -> pathlib.Path | io.BytesIO:
    """method to optimize PNG files using a pure python external optimizer"""

    ensure_matches(src, "PNG")

    img = Image.open(src)

    if options is None:
        options = OptimizePngOptions()

    if options.remove_transparency:
        img = remove_alpha(img, options.background_color)

    if options.reduce_colors:
        img, _, _ = do_reduce_colors(img, options.max_colors)

    if not options.fast_mode and img.mode == "P":
        img, _ = rebuild_palette(img)

    if dst is None:
        dst = io.BytesIO()
    img.save(dst, optimize=True, format="PNG")
    if not isinstance(dst, pathlib.Path):
        dst.seek(0)
    return dst


@dataclass
class OptimizeJpgOptions:
    """Dataclass holding JPG optimization options

    Arguments:
        quality: JPEG quality (integer between 1 and 100)
            values: 50 | 55 | 35 | 100 | XX
        keep_exif: Whether to keep EXIF data in JPEG (boolean)
            values: True | False
        fast_mode: Use the supplied quality value. If turned off, optimizer will
                get dynamic quality value to ensure better compression
            values: True | False
    """

    quality: int | None = 85
    fast_mode: bool | None = True
    keep_exif: bool | None = True


def optimize_jpeg(
    src: pathlib.Path | io.BytesIO,
    dst: pathlib.Path | io.BytesIO | None = None,
    options: OptimizeJpgOptions | None = None,
) -> pathlib.Path | io.BytesIO:
    """method to optimize JPEG files using a pure python external optimizer"""

    if options is None:
        options = OptimizeJpgOptions()

    ensure_matches(src, "JPEG")

    img = Image.open(src)
    orig_size = (
        os.path.getsize(src)
        if isinstance(src, pathlib.Path)
        else src.getbuffer().nbytes
    )

    had_exif = False
    if (
        not isinstance(src, pathlib.Path)
        and piexif.load(src.getvalue())[  # pyright: ignore[reportUnknownMemberType]
            "Exif"
        ]
    ) or (
        isinstance(src, pathlib.Path)
        and piexif.load(str(src))["Exif"]  # pyright: ignore[reportUnknownMemberType]
    ):
        had_exif = True

    # only use progressive if file size is bigger
    use_progressive_jpg = orig_size > 10240  # 10KiB  # noqa: PLR2004

    if options.fast_mode:
        quality_setting = options.quality
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

    if options.keep_exif and had_exif:
        piexif.transplant(  # pyright: ignore[reportUnknownMemberType]
            exif_src=(
                str(src.resolve()) if isinstance(src, pathlib.Path) else src.getvalue()
            ),
            image=(
                str(dst.resolve()) if isinstance(dst, pathlib.Path) else dst.getvalue()
            ),
            new_file=dst,
        )

    return dst


@dataclass
class OptimizeWebpOptions:
    """Dataclass holding WebP optimization options

    Arguments:
        lossless: Whether to use lossless compression (boolean);
            values: True | False
        quality: WebP quality for lossy, effort put into compression for lossless
            (integer between 0 to 100);
            values: 30 | 45 | 100 | XX
        method: Quality/speed trade-off; higher values give better compression (integer
            between 1 and 6);
            values: 1 | 2 | 3 | 4 | 5 | 6

    refer to the link for more details
    https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#webp
    """

    quality: int | None = 60
    method: int | None = 6
    lossless: bool | None = False


def optimize_webp(
    src: pathlib.Path | io.BytesIO,
    dst: pathlib.Path | io.BytesIO | None = None,
    options: OptimizeWebpOptions | None = None,
) -> pathlib.Path | io.BytesIO:
    """method to optimize WebP using Pillow options"""

    if options is None:
        options = OptimizeWebpOptions()

    ensure_matches(src, "WEBP")
    params: dict[str, bool | int | None] = {
        "lossless": options.lossless,
        "quality": options.quality,
        "method": options.method,
    }

    webp_image = Image.open(src)
    if dst is None:
        dst = io.BytesIO()
        webp_image.save(dst, format="WEBP", **params)
        dst.seek(0)
    else:
        try:
            save_image(webp_image, dst, fmt="WEBP", **params)
        except Exception as exc:  # pragma: no cover
            if (
                isinstance(src, pathlib.Path)
                and isinstance(dst, pathlib.Path)
                and src.resolve() != dst.resolve()
                and dst.exists()
            ):
                dst.unlink()
            raise exc
    return dst


@dataclass
class OptimizeGifOptions:
    """Dataclass holding GIF optimization options

    Arguments:
        optimize_level: Optimization level; higher values give better compression
            (integer between 1 and 3);
            values: 1 | 2 | 3
        lossiness: Level of lossy optimization to use; higher values give better
            compression (integer)
            values: 20 | 45 | 80 | XX
        interlace: Whether to interlace the frames (boolean)
            values: True | False
        no_extensions: Whether to remove all extension options from GIF (boolean)
            values: True | False
        max_colors: Maximum number of colors in resultant GIF;
            (integer between 2 and 256)
            values: 2 | 86 | 128 | 256 | XX

    refer to the link for more details - https://www.lcdf.org/gifsicle/man.html
    """

    optimize_level: int | None = 1
    lossiness: int | None = None
    max_colors: int | None = None
    interlace: bool | None = True
    no_extensions: bool | None = True


def optimize_gif(
    src: pathlib.Path, dst: pathlib.Path, options: OptimizeGifOptions | None = None
) -> pathlib.Path:
    """method to optimize GIFs using gifsicle >= 1.92"""

    if options is None:
        options = OptimizeGifOptions()

    ensure_matches(src, "GIF")

    # use gifsicle
    args = ["/usr/bin/env", "gifsicle"]
    if options.optimize_level:
        args += [f"-O{options.optimize_level}"]
    if options.max_colors:
        args += ["--colors", str(options.max_colors)]
    if options.lossiness:
        args += [f"--lossy={options.lossiness}"]
    if options.no_extensions:
        args += ["--no-extensions"]
    if options.interlace:
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


@dataclass
class OptimizeOptions:
    """Dataclass holding optimization options for all supported formats"""

    gif: OptimizeGifOptions
    webp: OptimizeWebpOptions
    jpg: OptimizeJpgOptions
    png: OptimizePngOptions

    @classmethod
    def of(
        cls,
        gif: OptimizeGifOptions | None = None,
        webp: OptimizeWebpOptions | None = None,
        jpg: OptimizeJpgOptions | None = None,
        png: OptimizePngOptions | None = None,
    ):
        """Helper to override only few options from default value"""
        return OptimizeOptions(
            gif=gif or OptimizeGifOptions(),
            png=png or OptimizePngOptions(),
            webp=webp or OptimizeWebpOptions(),
            jpg=jpg or OptimizeJpgOptions(),
        )


def optimize_image(
    src: pathlib.Path,
    dst: pathlib.Path,
    options: OptimizeOptions | None = None,
    *,
    delete_src: bool | None = False,
    convert: bool | str | None = False,
):
    """Optimize image, automatically selecting correct optimizer

    Arguments:
        delete_src: whether to remove src file upon success (boolean)
            values: True | False
        convert: whether/how to convert from source before optimizing (str or boolean)
            values: False: don't convert
                    True: convert to format implied by dst suffix
                    "FMT": convert to format FMT (use Pillow names)"""

    if options is None:
        options = OptimizeOptions.of()

    src_format, dst_format = format_for(src, from_suffix=False), format_for(dst)

    if src_format is None:  # pragma: no cover
        # never supposed to happens since we get format from suffix, but good for type
        # checker + code safety / clean errors
        raise ValueError("Impossible to guess format from src image")
    if dst_format is None:
        raise ValueError("Impossible to guess format from dst image")
    # if requested, convert src to requested format into dst path
    if convert and src_format != dst_format:
        src_format = dst_format = convert if isinstance(convert, str) else dst_format
        convert_image(src, dst, fmt=src_format)
        src_img = pathlib.Path(dst)
    else:
        src_img = pathlib.Path(src)

    src_format = src_format.lower()
    if src_format in ("jpg", "jpeg"):
        optimize_jpeg(src=src_img, dst=dst, options=options.jpg)
    elif src_format == "gif":
        optimize_gif(src=src_img, dst=dst, options=options.gif)
    elif src_format == "png":
        optimize_png(src=src_img, dst=dst, options=options.png)
    elif src_format == "webp":
        optimize_webp(src=src_img, dst=dst, options=options.webp)
    else:
        raise NotImplementedError(
            f"Image format '{src_format}' cannot yet be optimized"
        )

    # delete src image if requested
    if delete_src and src.exists() and src.resolve() != dst.resolve():
        src.unlink()
