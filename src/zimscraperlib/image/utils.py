from __future__ import annotations

import pathlib
from typing import IO, Any

from PIL.Image import Image
from PIL.ImageFile import ImageFile


def save_image(
    src: Image | ImageFile,
    dst: pathlib.Path | IO[bytes],
    fmt: str,
    **params: Any,
) -> None:
    """PIL.Image.save() wrapper setting default parameters"""
    args = {"JPEG": {"quality": 100}, "PNG": {}}.get(fmt, {})
    args.update(params or {})
    src.save(dst, fmt, **args)
