#!/usr/bin/env python3
# vim: ai ts=4 sts=4 et sw=4 nu

from __future__ import annotations

import inspect
import io
import os
import pathlib
import re
import shutil
from subprocess import CalledProcessError

import piexif
import pytest
from PIL import Image
from resizeimage.imageexceptions import ImageSizeError

from zimscraperlib.image import presets
from zimscraperlib.image.conversion import (
    convert_image,
    convert_svg2png,
    create_favicon,
)
from zimscraperlib.image.optimization import (
    ensure_matches,
    get_optimization_method,
    optimize_gif,
    optimize_image,
    optimize_jpeg,
    optimize_png,
    optimize_webp,
)
from zimscraperlib.image.presets import (
    GifHigh,
    GifLow,
    GifMedium,
    JpegHigh,
    JpegLow,
    JpegMedium,
    PngHigh,
    PngLow,
    PngMedium,
    WebpHigh,
    WebpLow,
    WebpMedium,
)
from zimscraperlib.image.probing import (
    format_for,
    get_colors,
    is_hex_color,
    is_valid_image,
)
from zimscraperlib.image.transformation import resize_image
from zimscraperlib.image.utils import save_image

ALL_PRESETS = [(n, p) for n, p in inspect.getmembers(presets) if inspect.isclass(p)]


def get_image_size(fpath):
    return Image.open(fpath).size


def get_src_dst(
    tmp_path: pathlib.Path,
    fmt,
    png_image: pathlib.Path | None = None,
    jpg_image: pathlib.Path | None = None,
    gif_image: pathlib.Path | None = None,
    webp_image: pathlib.Path | None = None,
    svg_image: pathlib.Path | None = None,
) -> tuple[pathlib.Path, pathlib.Path]:
    options = {
        "png": png_image,
        "jpg": jpg_image,
        "webp": webp_image,
        "gif": gif_image,
        "svg": svg_image,
    }
    if fmt not in options:
        raise LookupError(f"Unsupported fmt passed: {fmt}")
    src = options[fmt]
    if not src:
        raise LookupError(f"fmt passed has no corresponding argument: {fmt}")
    else:
        return (src, tmp_path / f"out.{fmt}")


@pytest.mark.parametrize(
    "value, valid",
    [
        ("#CECECE", True),
        ("white", False),
        ("#bada55", True),
        ("#003777", True),
        ("#800000", True),
        ("transparent", False),
        ("000000", False),
    ],
)
def test_is_hex_color(value, valid):
    if valid:
        assert is_hex_color(value)
    else:
        assert not is_hex_color(value)


def test_colors_noimage():
    with pytest.raises(FileNotFoundError):
        get_colors(pathlib.Path("nofile.here"))


def test_colors_png_nopalette(png_image):
    assert get_colors(png_image, use_palette=False) == ("#04659B", "#E7F6FF")


def test_colors_jpg_nopalette(jpg_image):
    assert get_colors(jpg_image, use_palette=False) == ("#C1BBB3", "#F4F3F1")


def test_colors_png_palette(png_image):
    assert get_colors(png_image, use_palette=True) == ("#9E0404", "#E7F6FF")


def test_colors_jpg_palette(jpg_image):
    assert get_colors(jpg_image, use_palette=True) == ("#221C1B", "#F4F3F1")


@pytest.mark.parametrize(
    "src_fmt,dst_fmt,params",
    [
        ("png", "png", None),
        ("jpg", "JPEG", {"quality": 50}),
    ],
)
def test_save_image(png_image, jpg_image, tmp_path, src_fmt, dst_fmt, params):
    src, dst = get_src_dst(tmp_path, src_fmt, png_image=png_image, jpg_image=jpg_image)
    img = Image.open(src)
    save_image(img, dst, fmt=dst_fmt, **(params or {}))
    assert pathlib.Path(dst).exists()


@pytest.mark.parametrize(
    "fmt",
    ["png", "jpg"],
)
def test_resize_thumbnail(png_image, jpg_image, tmp_path, fmt):
    src, dst = get_src_dst(tmp_path, fmt, png_image=png_image, jpg_image=jpg_image)

    width, height = 100, 50
    resize_image(src, width, height, dst=dst, method="thumbnail")
    tw, th = get_image_size(dst)
    assert tw <= width
    assert th <= height


@pytest.mark.parametrize(
    "fmt",
    ["png", "jpg"],
)
def test_resize_bytestream(png_image, jpg_image, tmp_path, fmt):
    src, dst = get_src_dst(tmp_path, fmt, png_image=png_image, jpg_image=jpg_image)

    # copy image content into a bytes stream
    img = io.BytesIO()
    with open(src, "rb") as srch:
        img.write(srch.read())

    # resize in place (no dst)
    width, height = 100, 50
    resize_image(img, width, height, method="thumbnail")
    tw, th = get_image_size(img)
    assert tw <= width
    assert th <= height


@pytest.mark.parametrize(
    "fmt",
    ["png", "jpg"],
)
def test_resize_width(png_image, jpg_image, tmp_path, fmt):
    src, dst = get_src_dst(tmp_path, fmt, png_image=png_image, jpg_image=jpg_image)

    width, height = 100, 50
    resize_image(src, width, height, dst=dst, method="width")
    tw, _ = get_image_size(dst)
    assert tw == width


@pytest.mark.parametrize(
    "fmt",
    ["png", "jpg"],
)
def test_resize_height(png_image, jpg_image, tmp_path, fmt):
    src, dst = get_src_dst(tmp_path, fmt, png_image=png_image, jpg_image=jpg_image)

    width, height = 100, 50
    resize_image(src, width, height, dst=dst, method="height")
    _, th = get_image_size(dst)
    assert th == height


@pytest.mark.parametrize(
    "fmt",
    ["png", "jpg"],
)
def test_resize_crop(png_image, jpg_image, tmp_path, fmt):
    src, dst = get_src_dst(tmp_path, fmt, png_image=png_image, jpg_image=jpg_image)

    width, height = 5, 50
    resize_image(src, width, height, dst=dst, method="crop")
    tw, th = get_image_size(dst)
    assert tw == width
    assert th == height


@pytest.mark.parametrize(
    "fmt",
    ["png", "jpg"],
)
def test_resize_cover(png_image, jpg_image, tmp_path, fmt):
    src, dst = get_src_dst(tmp_path, fmt, png_image=png_image, jpg_image=jpg_image)

    width, height = 5, 50
    resize_image(src, width, height, dst=dst, method="cover")
    tw, th = get_image_size(dst)
    assert tw == width
    assert th == height


@pytest.mark.parametrize(
    "fmt",
    ["png", "jpg"],
)
def test_resize_contain(png_image, jpg_image, tmp_path, fmt):
    src, dst = get_src_dst(tmp_path, fmt, png_image=png_image, jpg_image=jpg_image)

    width, height = 5, 50
    resize_image(src, width, height, dst=dst, method="contain")
    tw, th = get_image_size(dst)
    assert tw <= width
    assert th <= height


@pytest.mark.parametrize(
    "fmt",
    ["png", "jpg"],
)
def test_resize_upscale(png_image, jpg_image, tmp_path, fmt):
    src, dst = get_src_dst(tmp_path, fmt, png_image=png_image, jpg_image=jpg_image)

    width, height = 500, 1000
    resize_image(src, width, height, dst=dst, method="cover")
    tw, th = get_image_size(dst)
    assert tw == width
    assert th == height


@pytest.mark.parametrize(
    "fmt",
    ["png", "jpg"],
)
def test_resize_small_image_error(png_image, jpg_image, tmp_path, fmt):
    src, dst = get_src_dst(tmp_path, fmt, png_image=png_image, jpg_image=jpg_image)

    width, height = 500, 1000
    with pytest.raises(ImageSizeError):
        resize_image(
            src,
            width,
            height,
            dst=dst,
            method="cover",
            allow_upscaling=False,
        )


@pytest.mark.parametrize(
    "src_fmt,dst_fmt,colorspace",
    [("png", "JPEG", "RGB"), ("png", "BMP", None), ("jpg", "JPEG", "CMYK")],
)
def test_change_image_format(
    png_image, jpg_image, tmp_path, src_fmt, dst_fmt, colorspace
):
    src, _ = get_src_dst(tmp_path, src_fmt, png_image=png_image, jpg_image=jpg_image)
    dst = tmp_path / f"out.{dst_fmt.lower()}"
    convert_image(src, dst, fmt=dst_fmt, colorspace=colorspace)
    dst_image = Image.open(dst)
    if colorspace:
        assert dst_image.mode == colorspace
    assert dst_image.format == dst_fmt


def test_change_image_format_defaults(png_image, tmp_path):
    # PNG to JPEG (loosing alpha)
    dst = tmp_path.joinpath(f"{png_image.stem}.jpg")
    convert_image(png_image, dst)
    dst_image = Image.open(dst)
    assert dst_image.mode == "RGB"
    assert dst_image.format == "JPEG"
    # PNG to WebP (keeping alpha)
    dst = tmp_path.joinpath(f"{png_image.stem}.webp")
    convert_image(png_image, dst)
    dst_image = Image.open(dst)
    assert dst_image.mode == "RGBA"
    assert dst_image.format == "WEBP"


def test_convert_io_src_dst(png_image: pathlib.Path):
    src = io.BytesIO(png_image.read_bytes())
    dst = io.BytesIO()
    convert_image(src, dst, fmt="PNG")
    dst_image = Image.open(dst)
    assert dst_image.format == "PNG"


def test_convert_io_src_path_dst(png_image: pathlib.Path, tmp_path: pathlib.Path):
    src = io.BytesIO(png_image.read_bytes())
    dst = tmp_path / "test.png"
    convert_image(src, dst, fmt="PNG")
    dst_image = Image.open(dst)
    assert dst_image.format == "PNG"


def test_convert_io_src_bad_dst(png_image: pathlib.Path, tmp_path: pathlib.Path):
    src = io.BytesIO(png_image.read_bytes())
    dst = tmp_path / "test.raster"
    with pytest.raises(
        ValueError, match="Impossible to guess destination image format"
    ):
        convert_image(src, dst)


def test_convert_path_src_io_dst(png_image: pathlib.Path):
    src = png_image
    dst = io.BytesIO()
    convert_image(src, dst, fmt="PNG")
    dst_image = Image.open(dst)
    assert dst_image.format == "PNG"


def test_convert_svg_io_src_path_dst(svg_image: pathlib.Path, tmp_path: pathlib.Path):
    src = io.BytesIO(svg_image.read_bytes())
    dst = tmp_path / "test.png"
    convert_svg2png(src, dst)
    dst_image = Image.open(dst)
    assert dst_image.format == "PNG"


def test_convert_svg_io_src_io_dst(svg_image: pathlib.Path):
    src = io.BytesIO(svg_image.read_bytes())
    dst = io.BytesIO()
    convert_svg2png(src, dst)
    dst_image = Image.open(dst)
    assert dst_image.format == "PNG"


def test_convert_svg_path_src_path_dst(svg_image: pathlib.Path, tmp_path: pathlib.Path):
    src = svg_image
    dst = tmp_path / "test.png"
    convert_svg2png(src, dst, width=96, height=96)
    dst_image = Image.open(dst)
    assert dst_image.format == "PNG"
    assert dst_image.width == 96
    assert dst_image.height == 96


def test_convert_svg_path_src_io_dst(svg_image: pathlib.Path):
    src = svg_image
    dst = io.BytesIO()
    convert_svg2png(src, dst, width=96, height=96)
    dst_image = Image.open(dst)
    assert dst_image.format == "PNG"
    assert dst_image.width == 96
    assert dst_image.height == 96


@pytest.mark.parametrize(
    "fmt,exp_size",
    [("png", 128), ("jpg", 128)],
)
def test_create_favicon(png_image2, jpg_image, tmp_path, fmt, exp_size):
    src, dst = get_src_dst(tmp_path, fmt, png_image=png_image2, jpg_image=jpg_image)
    dst = dst.parent.joinpath("favicon.ico")
    create_favicon(src, dst)

    im = Image.open(dst)
    assert im.format == "ICO"
    assert im.size == (exp_size, exp_size)


@pytest.mark.parametrize(
    "fmt",
    ["png", "jpg"],
)
def test_create_favicon_square(square_png_image, square_jpg_image, tmp_path, fmt):
    src, dst = get_src_dst(
        tmp_path, fmt, png_image=square_png_image, jpg_image=square_jpg_image
    )
    dst = dst.parent.joinpath("favicon.ico")
    create_favicon(src, dst)

    im = Image.open(dst)
    assert im.format == "ICO"
    assert im.size == (256, 256)


@pytest.mark.parametrize(
    "fmt",
    ["png", "jpg"],
)
def test_wrong_extension(square_png_image, square_jpg_image, tmp_path, fmt):
    src, dst = get_src_dst(
        tmp_path, fmt, png_image=square_png_image, jpg_image=square_jpg_image
    )
    with pytest.raises(ValueError):
        create_favicon(src, dst)


@pytest.mark.parametrize(
    "fmt",
    ["png", "jpg", "gif", "webp"],
)
def test_optimize_image_default(
    png_image2, jpg_image, gif_image, webp_image, tmp_path, fmt
):
    src, dst = get_src_dst(
        tmp_path,
        fmt,
        png_image=png_image2,
        jpg_image=jpg_image,
        gif_image=gif_image,
        webp_image=webp_image,
    )
    optimize_image(src, dst, delete_src=False)
    assert os.path.getsize(dst) < os.path.getsize(src)


def test_optimize_image_del_src(png_image, tmp_path):
    shutil.copy(png_image, tmp_path)
    src = tmp_path / png_image.name
    dst = tmp_path / "out.png"
    org_size = os.path.getsize(src)
    optimize_image(src, dst, delete_src=True)
    assert os.path.getsize(dst) < org_size
    assert not src.exists()


def test_optimize_image_allow_convert(png_image, tmp_path):
    shutil.copy(png_image, tmp_path)
    src = tmp_path / png_image.name
    dst = tmp_path / "out.webp"
    optimize_image(src, dst, delete_src=True, convert=True)
    assert not src.exists()
    assert dst.exists() and os.path.getsize(dst) > 0


def test_optimize_image_bad_dst(png_image, tmp_path):
    shutil.copy(png_image, tmp_path)
    src = tmp_path / png_image.name
    dst = tmp_path / "out.raster"
    with pytest.raises(ValueError, match="Impossible to guess format from dst image"):
        optimize_image(src, dst, delete_src=True, convert=True)


@pytest.mark.parametrize(
    "preset,expected_version,options,fmt",
    [
        (WebpLow(), 1, {"lossless": False, "quality": 40, "method": 6}, "webp"),
        (WebpMedium(), 1, {"lossless": False, "quality": 50, "method": 6}, "webp"),
        (WebpHigh(), 1, {"lossless": False, "quality": 90, "method": 6}, "webp"),
        (
            GifLow(),
            1,
            {
                "optimize_level": 3,
                "max_colors": 256,
                "lossiness": 80,
                "no_extensions": True,
                "interlace": True,
            },
            "gif",
        ),
        (
            GifMedium(),
            1,
            {
                "optimize_level": 3,
                "lossiness": 20,
                "no_extensions": True,
                "interlace": True,
            },
            "gif",
        ),
        (
            GifHigh(),
            1,
            {
                "optimize_level": 2,
                "lossiness": None,
                "no_extensions": True,
                "interlace": True,
            },
            "gif",
        ),
        (
            PngLow(),
            1,
            {
                "reduce_colors": True,
                "remove_transparency": False,
                "max_colors": 256,
                "fast_mode": False,
            },
            "png",
        ),
        (
            PngMedium(),
            1,
            {"reduce_colors": False, "remove_transparency": False, "fast_mode": False},
            "png",
        ),
        (
            PngHigh(),
            1,
            {"reduce_colors": False, "remove_transparency": False, "fast_mode": True},
            "png",
        ),
        (JpegLow(), 1, {"quality": 45, "keep_exif": False, "fast_mode": True}, "jpg"),
        (
            JpegMedium(),
            1,
            {"quality": 65, "keep_exif": False, "fast_mode": True},
            "jpg",
        ),
        (JpegHigh(), 1, {"quality": 80, "keep_exif": True, "fast_mode": True}, "jpg"),
    ],
)
def test_preset(
    preset,
    expected_version,
    options,
    fmt,
    png_image,
    jpg_image,
    gif_image,
    webp_image,
    tmp_path,
):
    assert preset.VERSION == expected_version
    assert preset.options == options
    src, dst = get_src_dst(
        tmp_path,
        fmt,
        png_image=png_image,
        jpg_image=jpg_image,
        gif_image=gif_image,
        webp_image=webp_image,
    )
    optimize_image(src, dst, delete_src=False, **preset.options)
    assert os.path.getsize(dst) < os.path.getsize(src)

    if fmt in ["jpg", "webp", "png"]:
        image_bytes = ""
        with open(src, "rb") as fl:
            image_bytes = fl.read()
        byte_stream = io.BytesIO(image_bytes)
        dst_bytes = get_optimization_method(fmt)(src=byte_stream, **preset.options)
        assert dst_bytes.getbuffer().nbytes < byte_stream.getbuffer().nbytes


def test_optimize_image_unsupported_format():
    src = pathlib.Path(__file__).parent.parent / "files" / "single_wave_icon.gbr"
    dst = pathlib.Path("image.png")
    with pytest.raises(
        NotImplementedError, match="Image format 'gbr' cannot yet be optimized"
    ):
        optimize_image(src, dst, delete_src=False)


def test_preset_has_mime_and_ext():
    for _, preset in ALL_PRESETS:
        assert preset().ext
        assert preset().mimetype.startswith("image/")


def test_remove_png_transparency(png_image, tmp_path):
    dst = tmp_path / "out.png"
    optimize_png(src=png_image, dst=dst, remove_transparency=True)
    assert os.path.getsize(dst) == 2352


def test_jpeg_exif_preserve(jpg_exif_image, tmp_path):
    # in filesystem
    dst = tmp_path / "out.jpg"
    optimize_jpeg(src=jpg_exif_image, dst=dst)
    assert piexif.load(str(dst))["Exif"] and (
        piexif.load(str(dst))["Exif"]
        == piexif.load(str(jpg_exif_image.resolve()))["Exif"]
    )

    # in memory
    with open(jpg_exif_image, "rb") as fl:
        src_bytes = fl.read()
    optimized_img = optimize_jpeg(src=io.BytesIO(src_bytes))
    assert isinstance(optimized_img, io.BytesIO)
    assert piexif.load(optimized_img.getvalue())["Exif"] and (
        piexif.load(src_bytes)["Exif"] == piexif.load(optimized_img.getvalue())["Exif"]
    )


def test_dynamic_jpeg_quality(jpg_image, tmp_path):
    # check optimization without fast mode
    dst = tmp_path / "out.jpg"
    optimize_jpeg(src=jpg_image, dst=dst, fast_mode=False)
    assert os.path.getsize(dst) < os.path.getsize(jpg_image)


def test_ensure_matches(webp_image):
    with pytest.raises(ValueError, match=re.escape("is not of format")):
        ensure_matches(webp_image, "PNG")


@pytest.mark.parametrize(
    "fmt,expected",
    [("png", "PNG"), ("jpg", "JPEG"), ("gif", "GIF"), ("webp", "WEBP"), ("svg", "SVG")],
)
def test_format_for_real_images_suffix(
    png_image, jpg_image, gif_image, webp_image, svg_image, tmp_path, fmt, expected
):
    src, _ = get_src_dst(
        tmp_path,
        fmt,
        png_image=png_image,
        jpg_image=jpg_image,
        gif_image=gif_image,
        webp_image=webp_image,
        svg_image=svg_image,
    )
    assert format_for(src) == expected


@pytest.mark.parametrize(
    "fmt,expected",
    [("png", "PNG"), ("jpg", "JPEG"), ("gif", "GIF"), ("webp", "WEBP"), ("svg", "SVG")],
)
def test_format_for_real_images_content_path(
    png_image, jpg_image, gif_image, webp_image, svg_image, tmp_path, fmt, expected
):
    src, _ = get_src_dst(
        tmp_path,
        fmt,
        png_image=png_image,
        jpg_image=jpg_image,
        gif_image=gif_image,
        webp_image=webp_image,
        svg_image=svg_image,
    )
    assert format_for(src, from_suffix=False) == expected


@pytest.mark.parametrize(
    "fmt,expected",
    [("png", "PNG"), ("jpg", "JPEG"), ("gif", "GIF"), ("webp", "WEBP"), ("svg", "SVG")],
)
def test_format_for_real_images_content_bytes(
    png_image, jpg_image, gif_image, webp_image, svg_image, tmp_path, fmt, expected
):
    src, _ = get_src_dst(
        tmp_path,
        fmt,
        png_image=png_image,
        jpg_image=jpg_image,
        gif_image=gif_image,
        webp_image=webp_image,
        svg_image=svg_image,
    )
    assert format_for(io.BytesIO(src.read_bytes()), from_suffix=False) == expected


@pytest.mark.parametrize(
    "src,expected",
    [
        ("image.png", "PNG"),
        ("image.jpg", "JPEG"),
        ("image.gif", "GIF"),
        ("image.webp", "WEBP"),
        ("image.svg", "SVG"),
        ("image.raster", None),
    ],
)
def test_format_for_from_suffix(src, expected):
    assert format_for(src=pathlib.Path(src), from_suffix=True) == expected


def test_format_for_cannot_use_suffix_with_byte_array():
    with pytest.raises(
        ValueError,
        match="Cannot guess image format from file suffix when byte array is passed",
    ):
        assert format_for(src=io.BytesIO(), from_suffix=True)


def test_optimize_webp_gif_failure(tmp_path, webp_image, gif_image):
    dst = tmp_path.joinpath("image.img")

    # webp
    with pytest.raises(TypeError):
        optimize_webp(
            webp_image, dst, lossless="bad"  # pyright: ignore[reportArgumentType]
        )
    assert not dst.exists()

    # gif
    dst.touch()  # fake temp file created during optim (actually fails before)
    with pytest.raises(CalledProcessError):
        optimize_gif(
            gif_image, dst, optimize_level="bad"  # pyright: ignore[reportArgumentType]
        )
    assert not dst.exists()


def test_wrong_extension_optim(tmp_path, png_image):
    dst = tmp_path.joinpath("image.jpg")
    shutil.copy(png_image, dst)
    with pytest.raises(ValueError, match=re.escape("is not of format JPEG")):
        optimize_jpeg(dst, dst)


def test_is_valid_image(png_image, png_image2, jpg_image, font):
    assert is_valid_image(png_image, "PNG")
    assert not is_valid_image(png_image, "JPEG")
    assert is_valid_image(jpg_image, "JPEG")
    assert is_valid_image(png_image, "PNG", (48, 48))
    assert not is_valid_image(png_image2, "PNG", (48, 48))
    assert not is_valid_image(b"", "PNG")
    assert not is_valid_image(34, "PNG")  # pyright: ignore[reportArgumentType]
    assert not is_valid_image(font, "PNG")
    with open(png_image, "rb") as fh:
        assert is_valid_image(fh.read(), "PNG", (48, 48))
        fh.seek(0)
        assert is_valid_image(io.BytesIO(fh.read()), "PNG", (48, 48))


def test_optimize_gif_no_optimize_level(gif_image, tmp_path):
    optimize_gif(gif_image, tmp_path / "out.gif", delete_src=False, optimize_level=None)


def test_optimize_gif_no_no_extensions(gif_image, tmp_path):
    optimize_gif(gif_image, tmp_path / "out.gif", delete_src=False, no_extensions=None)


def test_optimize_gif_no_interlace(gif_image, tmp_path):
    optimize_gif(gif_image, tmp_path / "out.gif", delete_src=False, interlace=None)
