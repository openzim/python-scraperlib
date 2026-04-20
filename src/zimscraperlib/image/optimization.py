"""An image optimization module to optimize the following image formats:

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
  a bit less size than the original images but maintain a high quality."""

import io
import os
import pathlib
import subprocess
import tempfile
import warnings
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

from zimscraperlib.image.probing import format_for


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
    """method to convert (if needed) and optimize PNG files"""

    if options is None:
        options = OptimizePngOptions()

    with Image.open(src) as img:
        if options.remove_transparency:
            img = remove_alpha(img, options.background_color)  # noqa: PLW2901

        if options.reduce_colors:
            img, _, _ = do_reduce_colors(img, options.max_colors)  # noqa: PLW2901

        if not options.fast_mode and img.mode == "P":
            img, _ = rebuild_palette(img)  # noqa: PLW2901

        if dst is None:
            dst = io.BytesIO()

        try:
            img.save(dst, optimize=True, format="PNG")
            if isinstance(dst, io.BytesIO):
                dst.seek(0)
        except Exception as exc:  # pragma: no cover
            if isinstance(dst, pathlib.Path) and dst.exists():
                dst.unlink()
            raise exc

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
    """method to convert (if needed) and optimize JPEG files"""

    if options is None:
        options = OptimizeJpgOptions()

    src_format = format_for(src, from_suffix=False)

    if isinstance(src, io.BytesIO):
        src.seek(0)

    with Image.open(src) as img:
        orig_size = (
            os.path.getsize(src)
            if isinstance(src, pathlib.Path)
            else src.getbuffer().nbytes
        )

        had_exif = False
        if src_format == "JPEG":
            if (
                not isinstance(src, pathlib.Path)
                and piexif.load(  # pyright: ignore[reportUnknownMemberType]
                    src.getvalue()
                )["Exif"]
            ) or (
                isinstance(src, pathlib.Path)
                and piexif.load(str(src))[  # pyright: ignore[reportUnknownMemberType]
                    "Exif"
                ]
            ):
                had_exif = True

        if src_format != "JPEG" and img.mode == "RGBA":
            img = img.convert("RGB")  # noqa: PLW2901

        # only use progressive if file size is bigger
        use_progressive_jpg = orig_size > 10240  # 10KiB  # noqa: PLR2004

        if options.fast_mode:
            quality_setting = options.quality
        else:
            quality_setting, _ = jpeg_dynamic_quality(img)

        if dst is None:
            dst = io.BytesIO()

        try:
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
                        str(src.resolve())
                        if isinstance(src, pathlib.Path)
                        else src.getvalue()
                    ),
                    image=(
                        str(dst.resolve())
                        if isinstance(dst, pathlib.Path)
                        else dst.getvalue()
                    ),
                    new_file=dst,
                )
        except Exception as exc:  # pragma: no cover
            if isinstance(dst, pathlib.Path) and dst.exists():
                dst.unlink()
            raise exc

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
    """method to convert (if needed) and optimize WebP using Pillow options"""

    if options is None:
        options = OptimizeWebpOptions()

    params: dict[str, bool | int | None] = {
        "lossless": options.lossless,
        "quality": options.quality,
        "method": options.method,
    }

    with Image.open(src) as img:
        if dst is None:
            dst = io.BytesIO()

        try:
            img.save(dst, format="WEBP", **params)
            if isinstance(dst, io.BytesIO):
                dst.seek(0)
        except Exception as exc:  # pragma: no cover
            if isinstance(dst, pathlib.Path) and dst.exists():
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
    src: pathlib.Path | io.BytesIO,
    dst: pathlib.Path | io.BytesIO,
    options: OptimizeGifOptions | None = None,
) -> pathlib.Path | io.BytesIO:
    """method to convert (if needed) and optimize GIFs using gifsicle >= 1.92"""

    if options is None:
        options = OptimizeGifOptions()

    temp_files: list[pathlib.Path] = []
    src_path = None

    try:
        src_format = format_for(src, from_suffix=False)

        if isinstance(src, io.BytesIO):
            src.seek(0)

        if src_format != "GIF":
            with tempfile.NamedTemporaryFile(suffix=".gif", delete=False) as tmp:
                src_path = pathlib.Path(tmp.name)
            temp_files.append(src_path)
            with Image.open(src) as img:
                if img.mode == "RGBA":
                    img = img.convert("RGB")  # noqa: PLW2901
                img.save(src_path, format="GIF")
        elif isinstance(src, io.BytesIO):
            with tempfile.NamedTemporaryFile(suffix=".gif", delete=False) as tmp:
                src_path = pathlib.Path(tmp.name)
            src_path.write_bytes(src.read())
            temp_files.append(src_path)
        else:
            src_path = src

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
        args += [str(src_path)]

        if isinstance(dst, io.BytesIO):
            gifsicle = subprocess.run(args, capture_output=True, check=False)
            if gifsicle.returncode != 0:
                dst.seek(0)
                dst.truncate()
            else:
                dst.write(gifsicle.stdout)
                dst.seek(0)
            gifsicle.check_returncode()
        else:
            with open(dst, "wb") as out_file:
                gifsicle = subprocess.run(args, stdout=out_file, check=False)
            # remove dst if gifsicle failed and src is different from dst
            if gifsicle.returncode != 0 and src_path != dst and dst.exists():
                dst.unlink()
            gifsicle.check_returncode()

    finally:
        for temp_file in temp_files:
            temp_file.unlink(missing_ok=True)

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
    src: pathlib.Path | io.BytesIO | bytes,
    dst: pathlib.Path | io.BytesIO,
    options: OptimizeOptions | None = None,
    *,
    dst_format: str | None = None,
    delete_src: bool = False,
    convert: bool | str = False,
) -> pathlib.Path | io.BytesIO:
    """Optimize image, automatically selecting correct optimizer

    Arguments:
        dst_format: format of the destination image,
            required when dst is io.BytesIO.
        delete_src: whether to remove src file upon success (boolean)
            values: True | False
        convert: will be deprecated in scraperlib 6, use dst_format instead.
            values: False: don't convert
                    True: convert to format implied by dst suffix
                    str: convert to the specified format"""

    if convert is not False:
        warnings.warn(
            "The 'convert' param is deprecated and will be removed in scraperlib 6."
            "Use 'dst_format' parameter instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        if isinstance(convert, str):
            dst_format = convert

    if options is None:
        options = OptimizeOptions.of()

    if isinstance(src, bytes):
        src = io.BytesIO(src)

    if delete_src and isinstance(src, io.BytesIO):
        raise ValueError("delete_src is not applicable when src is io.BytesIO or bytes")

    if isinstance(dst, pathlib.Path):
        dst_format = dst_format or format_for(dst)
        if dst_format is None:
            raise ValueError("Impossible to guess format from dst image")
    elif dst_format is None:
        raise ValueError("dst_format is required when dst is io.BytesIO")
    dst_format = dst_format.lower()

    if dst_format in ("jpg", "jpeg"):
        optimize_jpeg(src=src, dst=dst, options=options.jpg)
    elif dst_format == "gif":
        optimize_gif(src=src, dst=dst, options=options.gif)
    elif dst_format == "png":
        optimize_png(src=src, dst=dst, options=options.png)
    elif dst_format == "webp":
        optimize_webp(src=src, dst=dst, options=options.webp)
    else:
        raise NotImplementedError(
            f"Image format '{dst_format}' cannot yet be optimized"
        )

    if (
        delete_src
        and isinstance(src, pathlib.Path)
        and src.exists()
        and isinstance(dst, pathlib.Path)
        and dst.exists()
        and not src.samefile(dst)
    ):
        src.unlink()

    return dst
