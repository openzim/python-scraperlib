import inspect
import io
import os
import pathlib
import re
import shutil
from dataclasses import asdict, is_dataclass
from typing import Any

import piexif  # pyright: ignore[reportMissingTypeStubs]
import pytest
from PIL import Image
from resizeimage.imageexceptions import (  # pyright: ignore[reportMissingTypeStubs]
    ImageSizeError,
)

from zimscraperlib.image import presets
from zimscraperlib.image.conversion import (
    convert_image,
    convert_svg2png,
    create_favicon,
)
from zimscraperlib.image.optimization import (
    OptimizeGifOptions,
    OptimizeJpgOptions,
    OptimizeOptions,
    OptimizePngOptions,
    OptimizeWebpOptions,
    ensure_matches,
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

ALL_PRESETS = [
    (n, p)
    for n, p in inspect.getmembers(presets)
    if inspect.isclass(p) and not is_dataclass(p)
]


def get_image_size(fpath: pathlib.Path | io.BytesIO) -> tuple[int, int]:
    return Image.open(fpath).size


def get_src_dst(
    tmp_path: pathlib.Path,
    fmt: str,
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
def test_is_hex_color(value: str, *, valid: bool):
    if valid:
        assert is_hex_color(value)
    else:
        assert not is_hex_color(value)


def test_colors_noimage():
    with pytest.raises(FileNotFoundError):
        get_colors(pathlib.Path("nofile.here"))


def test_colors_png_nopalette(png_image: pathlib.Path):
    assert get_colors(png_image, use_palette=False) == ("#04659B", "#E7F6FF")


def test_colors_jpg_nopalette(jpg_image: pathlib.Path):
    assert get_colors(jpg_image, use_palette=False) == ("#C1BBB3", "#F4F3F1")


def test_colors_png_palette(png_image: pathlib.Path):
    assert get_colors(png_image, use_palette=True) == ("#9E0404", "#E7F6FF")


def test_colors_jpg_palette(jpg_image: pathlib.Path):
    assert get_colors(jpg_image, use_palette=True) == ("#221C1B", "#F4F3F1")


@pytest.mark.parametrize(
    "src_fmt,dst_fmt,params",
    [
        ("png", "png", None),
        ("jpg", "JPEG", {"quality": 50}),
    ],
)
def test_save_image(
    png_image: pathlib.Path,
    jpg_image: pathlib.Path,
    tmp_path: pathlib.Path,
    src_fmt: str,
    dst_fmt: str,
    params: dict[str, Any] | None,
):
    src, dst = get_src_dst(tmp_path, src_fmt, png_image=png_image, jpg_image=jpg_image)
    img = Image.open(src)
    save_image(img, dst, fmt=dst_fmt, **(params or {}))
    assert pathlib.Path(dst).exists()


@pytest.mark.parametrize(
    "fmt",
    ["png", "jpg"],
)
def test_resize_thumbnail(
    png_image: pathlib.Path, jpg_image: pathlib.Path, tmp_path: pathlib.Path, fmt: str
):
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
def test_resize_bytestream(
    png_image: pathlib.Path, jpg_image: pathlib.Path, tmp_path: pathlib.Path, fmt: str
):
    src, _ = get_src_dst(tmp_path, fmt, png_image=png_image, jpg_image=jpg_image)

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
def test_resize_width(
    png_image: pathlib.Path, jpg_image: pathlib.Path, tmp_path: pathlib.Path, fmt: str
):
    src, dst = get_src_dst(tmp_path, fmt, png_image=png_image, jpg_image=jpg_image)

    width, height = 100, 50
    resize_image(src, width, height, dst=dst, method="width")
    tw, _ = get_image_size(dst)
    assert tw == width


@pytest.mark.parametrize(
    "fmt",
    ["png", "jpg"],
)
def test_resize_height(
    png_image: pathlib.Path, jpg_image: pathlib.Path, tmp_path: pathlib.Path, fmt: str
):
    src, dst = get_src_dst(tmp_path, fmt, png_image=png_image, jpg_image=jpg_image)

    width, height = 100, 50
    resize_image(src, width, height, dst=dst, method="height")
    _, th = get_image_size(dst)
    assert th == height


@pytest.mark.parametrize(
    "fmt",
    ["png", "jpg"],
)
def test_resize_crop(
    png_image: pathlib.Path, jpg_image: pathlib.Path, tmp_path: pathlib.Path, fmt: str
):
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
def test_resize_cover(
    png_image: pathlib.Path, jpg_image: pathlib.Path, tmp_path: pathlib.Path, fmt: str
):
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
def test_resize_contain(
    png_image: pathlib.Path, jpg_image: pathlib.Path, tmp_path: pathlib.Path, fmt: str
):
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
def test_resize_upscale(
    png_image: pathlib.Path, jpg_image: pathlib.Path, tmp_path: pathlib.Path, fmt: str
):
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
def test_resize_small_image_error(
    png_image: pathlib.Path, jpg_image: pathlib.Path, tmp_path: pathlib.Path, fmt: str
):
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
    png_image: pathlib.Path,
    jpg_image: pathlib.Path,
    tmp_path: pathlib.Path,
    src_fmt: str,
    dst_fmt: str,
    colorspace: str | None,
):
    src, _ = get_src_dst(tmp_path, src_fmt, png_image=png_image, jpg_image=jpg_image)
    dst = tmp_path / f"out.{dst_fmt.lower()}"
    convert_image(src, dst, fmt=dst_fmt, colorspace=colorspace)
    dst_image = Image.open(dst)
    if colorspace:
        assert dst_image.mode == colorspace
    assert dst_image.format == dst_fmt


def test_change_image_format_defaults(png_image: pathlib.Path, tmp_path: pathlib.Path):
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
def test_create_favicon(
    png_image2: pathlib.Path,
    jpg_image: pathlib.Path,
    tmp_path: pathlib.Path,
    fmt: str,
    exp_size: int,
):
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
def test_create_favicon_square(
    square_png_image: pathlib.Path,
    square_jpg_image: pathlib.Path,
    tmp_path: pathlib.Path,
    fmt: str,
):
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
def test_wrong_extension(
    square_png_image: pathlib.Path,
    square_jpg_image: pathlib.Path,
    tmp_path: pathlib.Path,
    fmt: str,
):
    src, dst = get_src_dst(
        tmp_path, fmt, png_image=square_png_image, jpg_image=square_jpg_image
    )
    with pytest.raises(ValueError):
        create_favicon(src, dst)


@pytest.mark.parametrize(
    "fmt",
    ["png", "jpg", "gif", "webp"],
)
def test_optimize_image_default_generic(
    png_image2: pathlib.Path,
    jpg_image: pathlib.Path,
    gif_image: pathlib.Path,
    webp_image: pathlib.Path,
    tmp_path: pathlib.Path,
    fmt: str,
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


@pytest.mark.parametrize(
    "fmt",
    ["png", "jpg", "gif", "webp"],
)
def test_optimize_image_default_direct(
    png_image2: pathlib.Path,
    jpg_image: pathlib.Path,
    gif_image: pathlib.Path,
    webp_image: pathlib.Path,
    tmp_path: pathlib.Path,
    fmt: str,
):
    src, dst = get_src_dst(
        tmp_path,
        fmt,
        png_image=png_image2,
        jpg_image=jpg_image,
        gif_image=gif_image,
        webp_image=webp_image,
    )

    if fmt in ("jpg", "jpeg"):
        optimize_jpeg(src=src, dst=dst)
    elif fmt == "gif":
        optimize_gif(src=src, dst=dst)
    elif fmt == "png":
        optimize_png(src=src, dst=dst)
    elif fmt == "webp":
        optimize_webp(src=src, dst=dst)
    else:
        raise NotImplementedError(f"Image format '{fmt}' cannot yet be optimized")
    assert os.path.getsize(dst) < os.path.getsize(src)


def test_optimize_image_del_src(png_image: pathlib.Path, tmp_path: pathlib.Path):
    shutil.copy(png_image, tmp_path)
    src = tmp_path / png_image.name
    dst = tmp_path / "out.png"
    org_size = os.path.getsize(src)
    optimize_image(src, dst, delete_src=True)
    assert os.path.getsize(dst) < org_size
    assert not src.exists()


def test_optimize_image_allow_convert(png_image: pathlib.Path, tmp_path: pathlib.Path):
    shutil.copy(png_image, tmp_path)
    src = tmp_path / png_image.name
    dst = tmp_path / "out.webp"
    optimize_image(src, dst, delete_src=True, convert=True)
    assert not src.exists()
    assert dst.exists() and os.path.getsize(dst) > 0


def test_optimize_image_bad_dst(png_image: pathlib.Path, tmp_path: pathlib.Path):
    shutil.copy(png_image, tmp_path)
    src = tmp_path / png_image.name
    dst = tmp_path / "out.raster"
    with pytest.raises(ValueError, match="Impossible to guess format from dst image"):
        optimize_image(src, dst, delete_src=True, convert=True)


@pytest.mark.parametrize(
    "preset,expected_version,options",
    [
        (WebpLow(), 1, {"lossless": False, "quality": 40, "method": 6}),
        (WebpMedium(), 1, {"lossless": False, "quality": 50, "method": 6}),
        (WebpHigh(), 1, {"lossless": False, "quality": 90, "method": 6}),
    ],
)
def test_image_preset_webp(
    preset: WebpLow | WebpMedium | WebpHigh,
    expected_version: int,
    options: dict[str, str | bool | int | None],
    webp_image: pathlib.Path,
    tmp_path: pathlib.Path,
):
    assert preset.VERSION == expected_version
    assert preset.ext == "webp"
    assert preset.mimetype == "image/webp"

    default_options = OptimizeWebpOptions()
    preset_options = asdict(preset.options)

    for key, value in preset_options.items():
        assert value == (
            options[key] if key in options else getattr(default_options, key)
        )

    src = webp_image
    dst = tmp_path / f"out.{preset.ext}"
    optimize_image(
        src,
        tmp_path / f"out.{preset.ext}",
        delete_src=False,
        options=OptimizeOptions.of(webp=preset.options),
    )
    assert os.path.getsize(dst) < os.path.getsize(src)

    image_bytes = ""
    with open(src, "rb") as fl:
        image_bytes = fl.read()
    byte_stream = io.BytesIO(image_bytes)
    dst_bytes = optimize_webp(src=byte_stream, options=preset.options)
    assert isinstance(dst_bytes, io.BytesIO)
    assert dst_bytes.getbuffer().nbytes < byte_stream.getbuffer().nbytes


@pytest.mark.parametrize(
    "preset,expected_version,options",
    [
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
        ),
    ],
)
def test_image_preset_gif(
    preset: GifLow | GifMedium | GifHigh,
    expected_version: int,
    options: dict[str, str | bool | int | None],
    gif_image: pathlib.Path,
    tmp_path: pathlib.Path,
):
    assert preset.VERSION == expected_version
    assert preset.ext == "gif"
    assert preset.mimetype == "image/gif"

    default_options = OptimizeGifOptions()
    preset_options = asdict(preset.options)

    for key, value in preset_options.items():
        assert value == (
            options[key] if key in options else getattr(default_options, key)
        )

    src = gif_image
    dst = tmp_path / f"out.{preset.ext}"
    optimize_image(
        src,
        tmp_path / f"out.{preset.ext}",
        delete_src=False,
        options=OptimizeOptions.of(gif=preset.options),
    )
    assert os.path.getsize(dst) < os.path.getsize(src)


@pytest.mark.parametrize(
    "preset,expected_version,options",
    [
        (
            PngLow(),
            1,
            {
                "reduce_colors": True,
                "remove_transparency": False,
                "max_colors": 256,
                "fast_mode": False,
            },
        ),
        (
            PngMedium(),
            1,
            {"reduce_colors": False, "remove_transparency": False, "fast_mode": False},
        ),
        (
            PngHigh(),
            1,
            {"reduce_colors": False, "remove_transparency": False, "fast_mode": True},
        ),
    ],
)
def test_image_preset_png(
    preset: PngLow | PngMedium | PngHigh,
    expected_version: int,
    options: dict[str, str | bool | int | None],
    png_image: pathlib.Path,
    tmp_path: pathlib.Path,
):
    assert preset.VERSION == expected_version
    assert preset.ext == "png"
    assert preset.mimetype == "image/png"

    default_options = OptimizePngOptions()
    preset_options = asdict(preset.options)

    for key, value in preset_options.items():
        assert value == (
            options[key] if key in options else getattr(default_options, key)
        )

    src = png_image
    dst = tmp_path / f"out.{preset.ext}"
    optimize_image(
        src,
        tmp_path / f"out.{preset.ext}",
        delete_src=False,
        options=OptimizeOptions.of(png=preset.options),
    )
    assert os.path.getsize(dst) < os.path.getsize(src)

    image_bytes = ""
    with open(src, "rb") as fl:
        image_bytes = fl.read()
    byte_stream = io.BytesIO(image_bytes)
    dst_bytes = optimize_png(src=byte_stream, options=preset.options)
    assert isinstance(dst_bytes, io.BytesIO)
    assert dst_bytes.getbuffer().nbytes < byte_stream.getbuffer().nbytes


@pytest.mark.parametrize(
    "preset,expected_version,options",
    [
        (JpegLow(), 1, {"quality": 45, "keep_exif": False, "fast_mode": True}),
        (
            JpegMedium(),
            1,
            {"quality": 65, "keep_exif": False, "fast_mode": True},
        ),
        (JpegHigh(), 1, {"quality": 80, "keep_exif": True, "fast_mode": True}),
    ],
)
def test_image_preset_jpg(
    preset: JpegLow | JpegMedium | JpegHigh,
    expected_version: int,
    options: dict[str, str | bool | int | None],
    jpg_image: pathlib.Path,
    tmp_path: pathlib.Path,
):
    assert preset.VERSION == expected_version
    assert preset.ext == "jpg"
    assert preset.mimetype == "image/jpeg"

    default_options = OptimizeJpgOptions()
    preset_options = asdict(preset.options)

    for key, value in preset_options.items():
        assert value == (
            options[key] if key in options else getattr(default_options, key)
        )

    src = jpg_image
    dst = tmp_path / f"out.{preset.ext}"
    optimize_image(
        src,
        tmp_path / f"out.{preset.ext}",
        delete_src=False,
        options=OptimizeOptions.of(jpg=preset.options),
    )
    assert os.path.getsize(dst) < os.path.getsize(src)

    image_bytes = ""
    with open(src, "rb") as fl:
        image_bytes = fl.read()
    byte_stream = io.BytesIO(image_bytes)
    dst_bytes = optimize_jpeg(src=byte_stream, options=preset.options)
    assert isinstance(dst_bytes, io.BytesIO)
    assert dst_bytes.getbuffer().nbytes < byte_stream.getbuffer().nbytes


def test_optimize_image_unsupported_format():
    src = pathlib.Path(__file__).parent.parent / "files" / "single_wave_icon.gbr"
    dst = pathlib.Path("image.png")
    with pytest.raises(
        NotImplementedError, match="Image format 'gbr' cannot yet be optimized"
    ):
        optimize_image(src, dst, delete_src=False)


def test_image_preset_has_mime_and_ext():
    for _, preset in ALL_PRESETS:
        assert preset().ext
        assert preset().mimetype.startswith("image/")


def test_remove_png_transparency(png_image: pathlib.Path, tmp_path: pathlib.Path):
    dst = tmp_path / "out.png"
    optimize_png(
        src=png_image, dst=dst, options=OptimizePngOptions(remove_transparency=True)
    )
    assert os.path.getsize(dst) == 2352


def test_jpeg_exif_preserve(jpg_exif_image: pathlib.Path, tmp_path: pathlib.Path):
    # in filesystem
    dst = tmp_path / "out.jpg"
    optimize_jpeg(src=jpg_exif_image, dst=dst)
    assert piexif.load(str(dst))[  # pyright: ignore[reportUnknownMemberType]
        "Exif"
    ] and (
        piexif.load(str(dst))["Exif"]  # pyright: ignore[reportUnknownMemberType]
        == piexif.load(  # pyright: ignore[reportUnknownMemberType]
            str(jpg_exif_image.resolve())
        )["Exif"]
    )

    # in memory
    with open(jpg_exif_image, "rb") as fl:
        src_bytes = fl.read()
    optimized_img = optimize_jpeg(src=io.BytesIO(src_bytes))
    assert isinstance(optimized_img, io.BytesIO)
    assert piexif.load(  # pyright: ignore[reportUnknownMemberType]
        optimized_img.getvalue()
    )["Exif"] and (
        piexif.load(src_bytes)["Exif"]  # pyright: ignore[reportUnknownMemberType]
        == piexif.load(  # pyright: ignore[reportUnknownMemberType]
            optimized_img.getvalue()
        )["Exif"]
    )


def test_dynamic_jpeg_quality(jpg_image: pathlib.Path, tmp_path: pathlib.Path):
    # check optimization without fast mode
    dst = tmp_path / "out.jpg"
    optimize_jpeg(src=jpg_image, dst=dst, options=OptimizeJpgOptions(fast_mode=False))
    assert os.path.getsize(dst) < os.path.getsize(jpg_image)


def test_ensure_matches(webp_image: pathlib.Path):
    with pytest.raises(ValueError, match=re.escape("is not of format")):
        ensure_matches(webp_image, "PNG")


@pytest.mark.parametrize(
    "fmt,expected",
    [("png", "PNG"), ("jpg", "JPEG"), ("gif", "GIF"), ("webp", "WEBP"), ("svg", "SVG")],
)
def test_format_for_real_images_suffix(
    png_image: pathlib.Path,
    jpg_image: pathlib.Path,
    gif_image: pathlib.Path,
    webp_image: pathlib.Path,
    svg_image: pathlib.Path,
    tmp_path: pathlib.Path,
    fmt: str,
    expected: str,
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
    png_image: pathlib.Path,
    jpg_image: pathlib.Path,
    gif_image: pathlib.Path,
    webp_image: pathlib.Path,
    svg_image: pathlib.Path,
    tmp_path: pathlib.Path,
    fmt: str,
    expected: str,
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
    png_image: pathlib.Path,
    jpg_image: pathlib.Path,
    gif_image: pathlib.Path,
    webp_image: pathlib.Path,
    svg_image: pathlib.Path,
    tmp_path: pathlib.Path,
    fmt: str,
    expected: str,
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
def test_format_for_from_suffix(src: str, expected: str):
    assert format_for(src=pathlib.Path(src), from_suffix=True) == expected


def test_format_for_cannot_use_suffix_with_byte_array():
    with pytest.raises(
        ValueError,
        match="Cannot guess image format from file suffix when byte array is passed",
    ):
        assert format_for(src=io.BytesIO(), from_suffix=True)


def test_wrong_extension_optim(tmp_path: pathlib.Path, png_image: pathlib.Path):
    dst = tmp_path.joinpath("image.jpg")
    shutil.copy(png_image, dst)
    with pytest.raises(ValueError, match=re.escape("is not of format JPEG")):
        optimize_jpeg(dst, dst)


def test_is_valid_image(
    png_image: pathlib.Path,
    png_image2: pathlib.Path,
    jpg_image: pathlib.Path,
    font: pathlib.Path,
):
    assert is_valid_image(png_image, "PNG")
    assert not is_valid_image(png_image, "JPEG")
    assert is_valid_image(jpg_image, "JPEG")
    assert is_valid_image(png_image, "PNG", (48, 48))
    assert not is_valid_image(png_image2, "PNG", (48, 48))
    assert not is_valid_image(b"", "PNG")
    assert not is_valid_image(font, "PNG")
    with open(png_image, "rb") as fh:
        assert is_valid_image(fh.read(), "PNG", (48, 48))
        fh.seek(0)
        assert is_valid_image(io.BytesIO(fh.read()), "PNG", (48, 48))


def test_optimize_gif_no_optimize_level(
    gif_image: pathlib.Path, tmp_path: pathlib.Path
):
    optimize_gif(
        gif_image, tmp_path / "out.gif", options=OptimizeGifOptions(optimize_level=None)
    )


def test_optimize_gif_no_no_extensions(gif_image: pathlib.Path, tmp_path: pathlib.Path):
    optimize_gif(
        gif_image, tmp_path / "out.gif", options=OptimizeGifOptions(no_extensions=None)
    )


def test_optimize_gif_no_interlace(gif_image: pathlib.Path, tmp_path: pathlib.Path):
    optimize_gif(
        gif_image, tmp_path / "out.gif", options=OptimizeGifOptions(interlace=None)
    )


@pytest.mark.parametrize(
    "fmt, preset",
    [
        ("png", "low"),
        ("jpg", "low"),
        ("gif", "low"),
        ("webp", "low"),
        ("png", "medium"),
        ("jpg", "medium"),
        ("gif", "medium"),
        ("webp", "medium"),
        ("png", "high"),
        ("jpg", "high"),
        ("gif", "high"),
        ("webp", "high"),
    ],
)
def test_optimize_any_image(
    png_image: pathlib.Path,
    jpg_image: pathlib.Path,
    gif_image: pathlib.Path,
    webp_image: pathlib.Path,
    tmp_path: pathlib.Path,
    fmt: str,
    preset: str,
):
    src, dst = get_src_dst(
        tmp_path,
        fmt,
        png_image=png_image,
        jpg_image=jpg_image,
        gif_image=gif_image,
        webp_image=webp_image,
    )
    # test call to optimize_image where src format is not set and all options are
    # different than default values, just checking that at least we can set these opts
    optimize_image(
        src,
        dst,
        options=OptimizeOptions(
            gif=(
                GifMedium.options
                if preset == "low"
                else GifHigh.options if preset == "high" else GifMedium.options
            ),
            webp=(
                WebpLow.options
                if preset == "low"
                else WebpHigh.options if preset == "high" else WebpMedium.options
            ),
            jpg=(
                JpegLow.options
                if preset == "low"
                else JpegHigh.options if preset == "high" else JpegMedium.options
            ),
            png=(
                PngLow.options
                if preset == "low"
                else PngHigh.options if preset == "high" else PngMedium.options
            ),
        ),
    )
    assert os.path.getsize(dst) < os.path.getsize(src)
