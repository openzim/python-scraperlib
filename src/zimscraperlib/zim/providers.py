#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 nu

""" libzim Providers accepting a `ref` arg to keep it away from garbage collection

    Use case is to pass it the Item instance that created the Provider so that the
    Item lives longer than the provider, thus allowing:
    - to keep a single copy of the data if it is to be indexed
        (and thus Provider instanced twice)
    - to release whatever needs to be once we know data won't be fetched anymore """

from __future__ import annotations

import io
import pathlib

import libzim.writer  # pyright: ignore
import requests

from zimscraperlib.download import _get_retry_adapter, stream_file


class FileProvider(libzim.writer.FileProvider):
    def __init__(
        self,
        filepath: pathlib.Path,
        size: int | None = None,  # noqa: ARG002
        ref: object | None = None,
    ):
        super().__init__(filepath)
        self.ref = ref


class StringProvider(libzim.writer.StringProvider):
    def __init__(self, content: str | bytes, ref: object | None = None):
        super().__init__(content)
        self.ref = ref


class FileLikeProvider(libzim.writer.ContentProvider):
    """Provider referrencing a file-like object

    Use this to keep a single-copy of a content in memory.
    Useful for indexed content"""

    def __init__(
        self,
        fileobj: io.IOBase,
        size: int | None = None,
        ref: object | None = None,
    ):
        super().__init__()
        self.ref = ref
        self.fileobj = fileobj
        self.size = size

        if self.size is None:
            self.size = size or self.fileobj.seek(0, io.SEEK_END)
            self.fileobj.seek(0, io.SEEK_SET)

    def get_size(self) -> int:
        return self.size  # pyright: ignore

    def gen_blob(self) -> libzim.writer.Blob:
        yield libzim.writer.Blob(  # pragma: no cover
            self.fileobj.getvalue()  # pyright: ignore
        )


class URLProvider(libzim.writer.ContentProvider):
    """Provider downloading content as it is consumed by the libzim

    Useful for non-indexed content for which feed() is called only once"""

    def __init__(self, url: str, size: int | None = None, ref: object | None = None):
        super().__init__()
        self.url = url
        self.size = size if size is not None else self.get_size_of(url)
        self.ref = ref

        session = requests.Session()
        session.mount("http", _get_retry_adapter())
        self.resp = session.get(url, stream=True)
        self.resp.raise_for_status()

    @staticmethod
    def get_size_of(url) -> int | None:
        _, headers = stream_file(url, byte_stream=io.BytesIO(), only_first_block=True)
        try:
            return int(headers["Content-Length"])
        except Exception:
            return None

    def get_size(self) -> int:
        return self.size  # pyright: ignore

    def gen_blob(self) -> libzim.writer.Blob:  # pragma: no cover
        for chunk in self.resp.iter_content(10 * 1024):
            if chunk:
                yield libzim.writer.Blob(chunk)
        yield libzim.writer.Blob(b"")
