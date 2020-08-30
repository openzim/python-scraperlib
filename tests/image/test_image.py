#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import pytest
import pathlib
import os
import shutil

from PIL import Image
from resizeimage.imageexceptions import ImageSizeError

from zimscraperlib.image.probing import get_colors, is_hex_color
from zimscraperlib.image.transformation import resize_image
from zimscraperlib.image.convertion import create_favicon, convert_image
from zimscraperlib.image.optimization import ImageOptimizer
from zimscraperlib.image import save_image
from zimscraperlib.image.presets import WebpLow, WebpHigh, GifLow, GifHigh, PngLow, PngHigh, JpegLow, JpegHigh



def get_image_size(fpath):
    return Image.open(fpath).size


def get_src_dst(
    tmp_path, fmt, png_image=None, jpg_image=None, gif_image=None, webp_image=None
):
    return (
        {"png": png_image, "jpg": jpg_image, "webp": webp_image, "gif": gif_image}.get(
            fmt
        ),
        tmp_path / f"out.{fmt}",
    )


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
        get_colors("nofile.here")


def test_colors_png_nopalette(png_image):
    assert get_colors(png_image, False) == ("#04649C", "#E7F6FF")


def test_colors_jpg_nopalette(jpg_image):
    assert get_colors(jpg_image, False) == ("#C1BBB3", "#F4F3F1")


def test_colors_png_palette(png_image):
    assert get_colors(png_image, True) == ("#04649C", "#FFE7E7")


def test_colors_jpg_palette(jpg_image):
    assert get_colors(jpg_image, True) == ("#221C1B", "#F4F3F1")


@pytest.mark.parametrize(
    "fmt,params",
    [("png", None), ("jpg", {"quality": 50})],
)
def test_save_image(png_image, jpg_image, tmp_path, fmt, params):
    src, dst = get_src_dst(tmp_path, fmt, png_image=png_image, jpg_image=jpg_image)
    img = Image.open(src)
    if params:
        save_image(img, dst, "JPEG" if fmt == "jpg" else fmt, **params)
    else:
        save_image(img, dst, "JPEG" if fmt == "jpg" else fmt)
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
        resize_image(src, width, height, dst=dst, method="cover", allow_upscaling=False)


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


def test_change_image_format_defaults(png_image, jpg_image, tmp_path):
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


@pytest.mark.parametrize(
    "fmt,exp_size",
    [("png", 128), ("jpg", 128)],
)
def test_create_favicon(png_image, jpg_image, tmp_path, fmt, exp_size):
    src, dst = get_src_dst(tmp_path, fmt, png_image=png_image, jpg_image=jpg_image)
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
    "fmt", ["png", "jpg"],
)
def test_optimize_png_jpg(png_image, jpg_image, tmp_path, fmt):
    optimizer = ImageOptimizer()
    src, dst = get_src_dst(tmp_path, fmt, png_image=png_image, jpg_image=jpg_image)
    optimizer.optimize_png_jpg(src, dst, image_format=fmt, override_options={})
    assert os.path.getsize(dst) < os.path.getsize(src)


def test_optimize_gif(gif_image, tmp_path):
    optimizer = ImageOptimizer()
    src = gif_image
    dst = tmp_path / "out.gif"
    override_options = {
        "optimize_level": 3,
        "max_colors": 256,
        "lossiness": 80,
        "no_extensions": True,
        "interlace": True,
    }
    optimizer.optimize_gif(src, dst, override_options=override_options)
    assert os.path.getsize(dst) < os.path.getsize(src)


def test_optimize_webp(webp_image, tmp_path):
    optimizer = ImageOptimizer()
    src = webp_image
    dst = tmp_path / "out.webp"
    override_options = {"lossless": False, "quality": 50, "method": 1}
    optimizer.optimize_webp(src, dst, override_options=override_options)
    assert os.path.getsize(dst) < os.path.getsize(src)


@pytest.mark.parametrize(
    "fmt", ["png", "jpg", "gif", "webp"],
)
def test_optimize_image(png_image, jpg_image, gif_image, webp_image, tmp_path, fmt):
    optimizer = ImageOptimizer()
    src, dst = get_src_dst(
        tmp_path,
        fmt,
        png_image=png_image,
        jpg_image=jpg_image,
        gif_image=gif_image,
        webp_image=webp_image,
    )
    optimizer.optimize_image(src, dst, delete_src=False)
    assert os.path.getsize(dst) < os.path.getsize(src)


def test_optimize_image_del_src(png_image, tmp_path):
    optimizer = ImageOptimizer()
    shutil.copy(png_image, tmp_path)
    src = tmp_path / png_image.name
    dst = tmp_path / "out.png"
    org_size = os.path.getsize(src)
    optimizer.optimize_image(src, dst, delete_src=True)
    assert os.path.getsize(dst) < org_size
    assert not src.exists()


def test_optimize_image_file_not_found(tmp_path):
    optimizer = ImageOptimizer()
    with pytest.raises(FileNotFoundError, match="image is not present"):
        optimizer.optimize_image(pathlib.Path("apple.png"), tmp_path / "out.png")


def test_optimize_image_unsupported_format(font, tmp_path):
    optimizer = ImageOptimizer()
    with pytest.raises(Exception, match="not supported for optimization"):
        optimizer.optimize_image(font, tmp_path / "out.png")


@pytest.mark.parametrize(
    "preset,expected_version,options", [
        (WebpLow(), 1, {"lossless": False, "quality": 40, "method": 6}),
        (WebpHigh(), 1, {"lossless": False, "quality": 65, "method": 6}),
        (GifLow(), 1, {"optimize_level": 3, "max_colors": 256, "lossiness": 90, "no_extensions": True, "interlace": True}),
        (GifHigh(), 1, {"optimize_level": 1, "lossiness": 50, "no_extensions": True, "interlace": True}),
        (PngLow(), 1, {"reduce_colors": True, "remove_transparency": False, "max_colors": 256, "fast_mode": False}),
        (PngHigh(), 1, {"reduce_colors": False, "remove_transparency": False, "fast_mode": True}),
        (JpegLow(), 1, {"quality": 40, "keep_exif": False, "fast_mode": False}),
        (JpegHigh(), 1, {"quality": 70, "keep_exif": False, "fast_mode": True}),
    ],
)
def test_preset(preset, expected_version, options):
    assert preset.VERSION == expected_version
    assert preset.options == options
