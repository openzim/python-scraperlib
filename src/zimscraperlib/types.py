#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 nu

""" File extensions to MIME-Type  mapping

    All libzim *articles* contains the mime-type of their content, for the libzim
    reader to properly return it.

    Providing accurate mime-type for ZIM Article is important to prevent broken features
    upon reading.
    Ex.: youtube scraper uses Web Assembly files (.wasm) for the WebM codecs.
    Without the proper mime-type, wasm files are returned as octet-stream and thus
    not loaded efficiently.

    Should your scraper need additional mapping, use mimetypes.add_type() and it will
    be automatically used. """

from __future__ import annotations

import mimetypes
import pathlib

ARTICLE_MIME: str = "text/html"
FALLBACK_MIME: str = "application/octet-stream"
FONT_MIMES: list[str] = [
    "font/ttf",
    "application/font-ttf",
    "font/sfnt",
    "application/font-sfnt",
    "font/woff",
    "application/font-woff",
    "font/woff2",
    "application/font-woff2",
    "application/vnd.ms-opentype",
    "application/vnd.ms-fontobject",
]


def get_mime_for_name(
    filename: str | pathlib.Path,
    fallback: str | None = FALLBACK_MIME,
    no_ext_to=ARTICLE_MIME,
) -> str:
    """MIME-Type string from a filename

    filename is a string, not a path (doesn't need to exist)
    MIME only guessed from file extension and not actual content.

    Filename with no extension are mapped to `no_ext_to`"""
    try:
        filename = pathlib.Path(filename)
        if not filename.suffix:
            return no_ext_to
        return (
            mimetypes.guess_type(f"{filename.stem}{filename.suffix}")[0] or fallback
        )  # pyright: ignore
    except Exception:
        return fallback  # pyright: ignore


def init_types():
    """supplement mimetypes with custom mapping"""
    for ext, mime in [
        (".vtt", "text/vtt"),
        # py36, py37
        (".wasm", "application/wasm"),
        # matched to SFNT on py36, py37
        (".ttf", "font/ttf"),
        (".otf", "font/otf"),
        (".woff", "font/woff"),
        (".woff2", "font/woff2"),
    ]:
        mimetypes.add_type(mime, ext, strict=True)


init_types()
