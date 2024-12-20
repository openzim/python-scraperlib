import io
import pathlib
from typing import Any

import cairosvg.svg  # pyright: ignore[reportMissingTypeStubs]
from PIL.Image import open as pilopen

from zimscraperlib.constants import ALPHA_NOT_SUPPORTED
from zimscraperlib.image.probing import format_for
from zimscraperlib.image.transformation import resize_image
from zimscraperlib.image.utils import save_image


def convert_image(
    src: pathlib.Path | io.BytesIO,
    dst: pathlib.Path | io.BytesIO,
    **params: str | None,
) -> None:
    """convert an image file from one format to another
    params: Image.save() parameters. Depends on dest format.
    params can include the following keys:
     - fmt: specify the dest format (otherwise guessed from extension)
            ex: JPEG, PNG, BMP (and other PIL formats)
     - colorspace: convert to this colorspace. Otherwise not converted unless
     target format has no halpha channel while source had. In this case converted
     to RGB. ex: RGB, ARGB, CMYK (and other PIL colorspaces)"""

    colorspace = params.get("colorspace")  # requested colorspace
    fmt = (
        str(params.pop("fmt")).upper() if params.get("fmt") else None
    )  # requested format
    if not fmt:
        fmt = format_for(dst)
    if not fmt:
        raise ValueError("Impossible to guess destination image format")
    with pilopen(src) as image:
        if (image.mode == "RGBA" and fmt in ALPHA_NOT_SUPPORTED) or colorspace:
            image = image.convert(colorspace or "RGB")  # noqa: PLW2901
        save_image(image, dst, fmt, **params)


def convert_svg2png(
    src: str | pathlib.Path | io.BytesIO,
    dst: pathlib.Path | io.BytesIO,
    width: int | None = None,
    height: int | None = None,
):
    """Convert a SVG to a PNG

    Output width and height might be specified if resize is needed.
    PNG background is transparent.
    """
    kwargs: dict[str, Any] = {}
    if isinstance(src, pathlib.Path):
        src = str(src)
    if isinstance(src, str):
        kwargs["url"] = src
    else:
        kwargs["bytestring"] = src.getvalue()
    if width:
        kwargs["output_width"] = width
    if height:
        kwargs["output_height"] = height
    if isinstance(dst, pathlib.Path):
        cairosvg.svg2png(  # pyright: ignore[reportUnknownMemberType]
            write_to=str(dst), **kwargs
        )
    else:
        result = cairosvg.svg2png(  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
            **kwargs
        )
        if not isinstance(result, bytes):
            raise Exception(
                "Unexpected type returned by cairosvg.svg2png"
            )  # pragma: no cover
        dst.write(result)


def create_favicon(src: pathlib.Path, dst: pathlib.Path) -> None:
    """generate a squared favicon from a source image"""
    if dst.suffix != ".ico":
        raise ValueError("favicon extension must be ICO")

    img = pilopen(src)
    w, h = img.size
    # resize image to square first
    if w != h:
        size = min([w, h])
        resized = dst.parent.joinpath(f"{src.stem}.tmp.{src.suffix}")
        resize_image(src, size, size, resized, "contain")
        img = pilopen(resized)
    # now convert to ICO
    save_image(img, dst, "ICO")
