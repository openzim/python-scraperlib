#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import pytest
import pathlib
import os
import shutil

from PIL import Image
from resizeimage.imageexceptions import ImageSizeError
from optimize_images.data_structures import Task

from zimscraperlib.image.probing import get_colors, is_hex_color, format_for
from zimscraperlib.image.transformation import resize_image
from zimscraperlib.image.convertion import create_favicon, convert_image
from zimscraperlib.image.optimization import (
    optimize_image,
    ensure_matches,
    optimize_webp,
    optimize_png,
    optimize_jpeg,
    optimize_gif,
    run_optimize_images_task,
)
from zimscraperlib.image import save_image
from zimscraperlib.image.presets import (
    WebpLow,
    WebpMedium,
    WebpHigh,
    GifLow,
    GifMedium,
    GifHigh,
    PngLow,
    PngMedium,
    PngHigh,
    JpegLow,
    JpegMedium,
    JpegHigh,
)


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
    "fmt",
    ["png", "jpg", "gif", "webp"],
)
def test_optimize_image_default(
    png_image, jpg_image, gif_image, webp_image, tmp_path, fmt
):
    src, dst = get_src_dst(
        tmp_path,
        fmt,
        png_image=png_image,
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


@pytest.mark.parametrize(
    "preset,expected_version,options,fmt",
    [
        (WebpLow(), 1, {"lossless": False, "quality": 40, "method": 6}, "webp"),
        (WebpMedium(), 1, {"lossless": False, "quality": 50, "method": 6}, "webp"),
        (WebpHigh(), 1, {"lossless": False, "quality": 60, "method": 6}, "webp"),
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
            {"reduce_colors": True, "remove_transparency": False, "fast_mode": False},
            "png",
        ),
        (
            PngHigh(),
            1,
            {"reduce_colors": False, "remove_transparency": False, "fast_mode": True},
            "png",
        ),
        (JpegLow(), 1, {"quality": 45, "keep_exif": False, "fast_mode": False}, "jpg"),
        (
            JpegMedium(),
            1,
            {"quality": 65, "keep_exif": False, "fast_mode": False},
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


def test_ensure_matches(webp_image):
    with pytest.raises(ValueError, match="is not of format"):
        ensure_matches(webp_image, "PNG")


@pytest.mark.parametrize(
    "fmt,expected",
    [("png", "PNG"), ("jpg", "JPEG"), ("gif", "GIF"), ("webp", "WEBP")],
)
def test_format_for(
    png_image, jpg_image, gif_image, webp_image, tmp_path, fmt, expected
):
    src, _ = get_src_dst(
        tmp_path,
        fmt,
        png_image=png_image,
        jpg_image=jpg_image,
        gif_image=gif_image,
        webp_image=webp_image,
    )
    assert format_for(src) == expected


def test_optimize_images_task_failure(tmp_path, font):
    tmp_fl = tmp_path / "tmp.jpg"
    dst = tmp_path / "out.jpg"

    # send an unreadable file

    tmp_fl.touch(mode=0o377)
    task = Task(
        src_path=str(tmp_fl.resolve()),
        quality=50,
        remove_transparency=False,
        reduce_colors=False,
        max_colors=256,
        max_w=0,
        max_h=0,
        keep_exif=False,
        convert_all=False,
        conv_big=False,
        force_del=False,
        bg_color=(255, 255, 255),
        grayscale=False,
        no_size_comparison=True,
        fast_mode=False,
    )
    with pytest.raises(Exception):
        run_optimize_images_task(task, tmp_fl, dst)

    assert not tmp_fl.exists()
    assert not dst.exists()


def test_optimize_webp_gif_failure(tmp_path, webp_image, gif_image):
    dst = tmp_path.joinpath("image.img")

    # webp
    with pytest.raises(Exception):
        optimize_webp(webp_image, dst, lossless="bad")
    assert not dst.exists()

    # gif
    dst.touch()  # fake temp file created during optim (actually fails before)
    with pytest.raises(Exception):
        optimize_gif(gif_image, dst, optimize_level="bad")
    assert not dst.exists()


def test_wrong_extension_optim(tmp_path, png_image):
    dst = tmp_path.joinpath("image.jpg")
    shutil.copy(png_image, dst)
    with pytest.raises(Exception):
        optimize_jpeg(dst, dst)
