import colorsys
import io
import pathlib
import re

import colorthief  # pyright: ignore[reportMissingTypeStubs]
import PIL.Image

from zimscraperlib.filesystem import get_content_mimetype, get_file_mimetype


def get_colors(
    src: pathlib.Path, *, use_palette: bool | None = True
) -> tuple[str, str]:
    """(main, secondary) HTML color codes from an image path"""

    def rgb_to_hex(r: int, g: int, b: int) -> str:
        """hexadecimal HTML-friendly color code for RGB tuple"""
        return "#{}{}{}".format(*[str(hex(x)[2:]).zfill(2) for x in (r, g, b)]).upper()

    def solarize(r: int, g: int, b: int) -> tuple[int, int, int]:
        # calculate solarized color for main
        h, _, s = colorsys.rgb_to_hls(float(r) / 256, float(g) / 256, float(b) / 256)
        r2, g2, b2 = (int(x * 256) for x in colorsys.hls_to_rgb(h, 0.95, s))
        return r2, g2, b2

    ct = colorthief.ColorThief(src)

    if use_palette:
        # extract two main colors from palette, solarizing second as background
        palette = ct.get_palette(  # pyright: ignore[reportUnknownVariableType]
            color_count=2, quality=1
        )

        # using the first two colors of the palette?
        mr, mg, mb = palette[0]  # pyright: ignore[reportUnknownVariableType]
        sr, sg, sb = solarize(*palette[1])  # pyright: ignore[reportUnknownArgumentType]
    else:
        # extract main color from image and solarize it as background
        mr, mg, mb = ct.get_color(  # pyright: ignore[reportUnknownVariableType]
            quality=1
        )
        sr, sg, sb = solarize(mr, mg, mb)  # pyright: ignore[reportUnknownArgumentType]

    return rgb_to_hex(
        mr, mg, mb  # pyright: ignore[reportUnknownArgumentType]
    ), rgb_to_hex(sr, sg, sb)


def is_hex_color(text: str) -> bool:
    """whether supplied text is a valid hex-formated color code"""
    return bool(re.search(r"^#(?:[0-9a-fA-F]{3}){1,2}$", text))


def format_for(
    src: pathlib.Path | io.BytesIO,
    *,
    from_suffix: bool = True,
) -> str | None:
    """Pillow format of a given filename, either Pillow-detected or from suffix"""
    if not from_suffix:
        try:
            with PIL.Image.open(src) as img:
                return img.format
        except PIL.UnidentifiedImageError:
            # Fallback based on mimetype for SVG which are not supported by PIL
            if (
                isinstance(src, pathlib.Path)
                and get_file_mimetype(src) == "image/svg+xml"
            ):
                return "SVG"
            elif (
                isinstance(src, io.BytesIO)
                and get_content_mimetype(src.getvalue()) == "image/svg+xml"
            ):
                return "SVG"
            else:  # pragma: no cover
                raise

    if not isinstance(src, pathlib.Path):
        raise ValueError(
            "Cannot guess image format from file suffix when byte array is passed"
        )

    from PIL.Image import EXTENSION as PIL_FMT_EXTENSION
    from PIL.Image import init as init_pil

    init_pil()  # populate the PIL_FMT_EXTENSION dictionary

    known_extensions = {".svg": "SVG"}
    known_extensions.update(PIL_FMT_EXTENSION)
    return known_extensions[src.suffix] if src.suffix in known_extensions else None


def is_valid_image(
    image: pathlib.Path | bytes | io.BytesIO,
    imformat: str,
    size: tuple[int, int] | None = None,
) -> bool:
    """whether image is a valid imformat (PNG) image, optionnaly of requested size"""
    if isinstance(image, bytes):
        image = io.BytesIO(image)
    try:
        img = PIL.Image.open(image)
        if img.format != imformat:
            return False
        if size and img.size != size:
            return False
    except Exception:
        return False
    return True
