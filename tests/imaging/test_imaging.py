#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import pytest

from PIL import Image
from resizeimage.imageexceptions import ImageSizeError

from zimscraperlib.imaging import get_colors, is_hex_color, resize_image, create_favicon


def get_image_size(fpath):
    return Image.open(fpath).size


def get_src_dst(png_image, jpg_image, tmp_path, fmt):
    return {"png": png_image, "jpg": jpg_image}.get(fmt), tmp_path / f"out.{fmt}"


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
    "fmt", ["png", "jpg"],
)
def test_resize_thumbnail(png_image, jpg_image, tmp_path, fmt):
    src, dst = get_src_dst(png_image, jpg_image, tmp_path, fmt)

    width, height = 100, 50
    resize_image(src, width, height, to=dst, method="thumbnail")
    tw, th = get_image_size(dst)
    assert tw <= width
    assert th <= height


@pytest.mark.parametrize(
    "fmt", ["png", "jpg"],
)
def test_resize_width(png_image, jpg_image, tmp_path, fmt):
    src, dst = get_src_dst(png_image, jpg_image, tmp_path, fmt)

    width, height = 100, 50
    resize_image(src, width, height, to=dst, method="width")
    tw, _ = get_image_size(dst)
    assert tw == width


@pytest.mark.parametrize(
    "fmt", ["png", "jpg"],
)
def test_resize_height(png_image, jpg_image, tmp_path, fmt):
    src, dst = get_src_dst(png_image, jpg_image, tmp_path, fmt)

    width, height = 100, 50
    resize_image(src, width, height, to=dst, method="height")
    _, th = get_image_size(dst)
    assert th == height


@pytest.mark.parametrize(
    "fmt", ["png", "jpg"],
)
def test_resize_crop(png_image, jpg_image, tmp_path, fmt):
    src, dst = get_src_dst(png_image, jpg_image, tmp_path, fmt)

    width, height = 5, 50
    resize_image(src, width, height, to=dst, method="crop")
    tw, th = get_image_size(dst)
    assert tw == width
    assert th == height


@pytest.mark.parametrize(
    "fmt", ["png", "jpg"],
)
def test_resize_cover(png_image, jpg_image, tmp_path, fmt):
    src, dst = get_src_dst(png_image, jpg_image, tmp_path, fmt)

    width, height = 5, 50
    resize_image(src, width, height, to=dst, method="cover")
    tw, th = get_image_size(dst)
    assert tw == width
    assert th == height


@pytest.mark.parametrize(
    "fmt", ["png", "jpg"],
)
def test_resize_contain(png_image, jpg_image, tmp_path, fmt):
    src, dst = get_src_dst(png_image, jpg_image, tmp_path, fmt)

    width, height = 5, 50
    resize_image(src, width, height, to=dst, method="contain")
    tw, th = get_image_size(dst)
    assert tw <= width
    assert th <= height


@pytest.mark.parametrize(
    "fmt", ["png", "jpg"],
)
def test_resize_upscale(png_image, jpg_image, tmp_path, fmt):
    src, dst = get_src_dst(png_image, jpg_image, tmp_path, fmt)

    width, height = 500, 1000
    resize_image(src, width, height, to=dst, method="cover")
    tw, th = get_image_size(dst)
    assert tw == width
    assert th == height


@pytest.mark.parametrize(
    "fmt", ["png", "jpg"],
)
def test_resize_small_image_error(png_image, jpg_image, tmp_path, fmt):
    src, dst = get_src_dst(png_image, jpg_image, tmp_path, fmt)

    width, height = 500, 1000
    with pytest.raises(ImageSizeError):
        resize_image(src, width, height, to=dst, method="cover", allow_upscaling=False)


@pytest.mark.parametrize(
    "fmt,exp_size", [("png", 128), ("jpg", 128)],
)
def test_create_favicon(png_image, jpg_image, tmp_path, fmt, exp_size):
    src, dst = get_src_dst(png_image, jpg_image, tmp_path, fmt)
    dst = dst.parent.joinpath("favicon.ico")
    create_favicon(src, dst)

    im = Image.open(dst)
    assert im.format == "ICO"
    assert im.size == (exp_size, exp_size)


@pytest.mark.parametrize(
    "fmt", ["png", "jpg"],
)
def test_create_favicon_square(square_png_image, square_jpg_image, tmp_path, fmt):
    src, dst = get_src_dst(square_png_image, square_jpg_image, tmp_path, fmt)
    dst = dst.parent.joinpath("favicon.ico")
    create_favicon(src, dst)

    im = Image.open(dst)
    assert im.format == "ICO"
    assert im.size == (256, 256)


@pytest.mark.parametrize(
    "fmt", ["png", "jpg"],
)
def test_wrong_extension(square_png_image, square_jpg_image, tmp_path, fmt):
    src, dst = get_src_dst(square_png_image, square_jpg_image, tmp_path, fmt)
    with pytest.raises(ValueError):
        create_favicon(src, dst)
