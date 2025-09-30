"""libzim Item helpers"""

import io
import pathlib
import re
import tempfile
import urllib.parse
from collections.abc import Callable
from typing import Any

import libzim.writer  # pyright: ignore[reportMissingModuleSource]

from zimscraperlib.download import stream_file
from zimscraperlib.filesystem import get_content_mimetype, get_file_mimetype
from zimscraperlib.zim.indexing import IndexData, get_pdf_index_data
from zimscraperlib.zim.providers import (
    FileLikeProvider,
    FileProvider,
    StringProvider,
    URLProvider,
)


class Item(libzim.writer.Item):
    """libzim.writer.Item returning props for path/title/mimetype"""

    def __init__(
        self,
        path: str | None = None,
        title: str | None = None,
        mimetype: str | None = None,
        hints: dict[libzim.writer.Hint, int] | None = None,
        **kwargs: Any,
    ):
        super().__init__()
        if path is not None:
            kwargs["path"] = path
        if title is not None:
            kwargs["title"] = title
        if mimetype is not None:
            kwargs["mimetype"] = mimetype
        if hints is not None:
            kwargs["hints"] = hints
        for k, v in kwargs.items():
            setattr(self, k, v)

    @property
    def should_index(self):
        return self.get_mimetype().startswith("text/html")

    def get_path(self) -> str:
        return getattr(self, "path", "")

    def get_title(self) -> str:
        return getattr(self, "title", "")

    def get_mimetype(self) -> str:
        return getattr(self, "mimetype", "")

    def get_hints(self) -> dict[libzim.writer.Hint, int]:
        return getattr(self, "hints", {})


def no_indexing_indexdata() -> IndexData:
    """IndexData asking libzim not to index this item"""
    return IndexData("", "")


class StaticItem(Item):
    """scraperlib Item with auto contentProvider from `content` or `filepath`

    Sets a `ref` to itself on the File/String content providers so it outlives them
    We need Item to survive its ContentProvider so that we can track lifecycle
    more efficiently: now when the libzim destroys the CP, python will destroy
    the Item and we can be notified that we're effectively through with our content

    By default, content is automatically indexed (either by the libzim itself for
    supported documents - text or html for now or by the python-scraperlib - only PDF
    supported for now). If you do not want this, set `auto_index` to False to disable
    both indexing (libzim and python-scraperlib).

    It is also possible to pass index_data to configure custom indexing of the item.

    If item title is not set by caller, it is automatically populated from index_data.
    """

    def __init__(
        self,
        content: str | bytes | None = None,
        fileobj: io.IOBase | None = None,
        filepath: pathlib.Path | None = None,
        path: str | None = None,
        title: str | None = None,
        mimetype: str | None = None,
        hints: dict[libzim.writer.Hint, int] | None = None,
        index_data: IndexData | None = None,
        *,
        auto_index: bool = True,
        **kwargs: Any,
    ):
        if content is not None:
            kwargs["content"] = content
        if fileobj is not None:
            kwargs["fileobj"] = fileobj
        if filepath is not None:
            kwargs["filepath"] = filepath
        super().__init__(
            path=path, title=title, mimetype=mimetype, hints=hints, **kwargs
        )
        if index_data:
            self.get_indexdata: Callable[[], IndexData] = lambda: index_data
        elif not auto_index:
            self.get_indexdata = no_indexing_indexdata  # index nothing
        else:
            self._get_auto_index()  # consider to add auto index

        # Populate item title from index data if title is not set by caller
        if (not getattr(self, "title", None)) and hasattr(self, "get_indexdata"):
            title = self.get_indexdata().get_title()
            if title:
                self.title = title

    def get_contentprovider(self) -> libzim.writer.ContentProvider:
        # content was set manually
        content = getattr(self, "content", None)
        if content is not None:
            if not isinstance(content, str | bytes):
                raise AttributeError(f"Unexpected type for content: {type(content)}")
            return StringProvider(content=content, ref=self)

        # using a file-like object
        fileobj = getattr(self, "fileobj", None)
        if fileobj:
            return FileLikeProvider(
                fileobj=fileobj, ref=self, size=getattr(self, "size", None)
            )

        # we had to download locally to get size
        filepath = getattr(self, "filepath", None)
        if filepath:
            return FileProvider(
                filepath=filepath, ref=self, size=getattr(self, "size", None)
            )

        raise NotImplementedError("No data to provide`")

    def _get_auto_index(self):
        """Populate item index data and title automatically from content"""

        # content was set manually
        content = getattr(self, "content", None)
        if content is not None:
            if not isinstance(content, str | bytes):
                raise RuntimeError(
                    f"Unexpected type for content: {type(content)}"
                )  # pragma: no cover
            mimetype = get_content_mimetype(
                content.encode("utf-8") if isinstance(content, str) else content
            )
            if mimetype == "application/pdf":
                index_data = get_pdf_index_data(content=content)
                self.get_indexdata = lambda: index_data
            else:
                return

        # using a file-like object
        fileobj = getattr(self, "fileobj", None)
        if fileobj:
            if not isinstance(fileobj, io.BytesIO):
                raise RuntimeError(
                    f"Unexpected type for content: {type(fileobj)}"
                )  # pragma: no cover
            mimetype = get_content_mimetype(fileobj.getvalue())
            if mimetype == "application/pdf":
                index_data = get_pdf_index_data(fileobj=fileobj)
                self.get_indexdata = lambda: index_data
            else:
                return

        # using a file path
        filepath = getattr(self, "filepath", None)
        if filepath:
            if not isinstance(filepath, pathlib.Path):
                raise RuntimeError(
                    f"Unexpected type for content: {type(filepath)}"
                )  # pragma: no cover
            mimetype = get_file_mimetype(filepath)
            if mimetype == "application/pdf":
                index_data = get_pdf_index_data(filepath=filepath)
                self.get_indexdata = (  # pyright:ignore [reportIncompatibleVariableOverride]
                    lambda: index_data
                )
            else:
                return


class URLItem(StaticItem):
    """StaticItem to automatically fetch and feed an URL resource

    Appropriate for retrieving/bundling static assets that you don't need to
    post-process.

    Uses URL's path as zim path if none provided
    Keeps single in-memory copy of content for HTML resources (indexed)
    Works transparently on servers returning a Content-Length header (most)
    *Swaps* a copy of the content either in memory or on disk (`use_disk=True`)
    in case the content size could not be retrieved from headers.
    Use `tmp_dir` to point location of that temp file."""

    @staticmethod
    def download_for_size(
        url: urllib.parse.ParseResult,
        tmp_dir: pathlib.Path | None = None,
        *,
        on_disk: bool,
    ):
        """Download URL to a temp file and return its tempfile and size"""
        fpath = stream = None
        if on_disk:
            suffix = pathlib.Path(re.sub(r"^/", "", url.path)).suffix
            fpath = pathlib.Path(
                tempfile.NamedTemporaryFile(
                    suffix=suffix, delete=False, dir=tmp_dir
                ).name
            )
        else:
            stream = io.BytesIO()
        size, _ = stream_file(url.geturl(), fpath=fpath, byte_stream=stream)
        return fpath or stream, size

    def __init__(
        self,
        url: str,
        path: str | None = None,
        title: str | None = None,
        mimetype: str | None = None,
        hints: dict[libzim.writer.Hint, int] | None = None,
        *,
        use_disk: bool | None = None,
        **kwargs: Any,
    ):
        if use_disk is not None:
            kwargs["use_disk"] = use_disk
        super().__init__(
            path=path, title=title, mimetype=mimetype, hints=hints, **kwargs
        )
        self.url = urllib.parse.urlparse(url)
        use_disk_set: bool = getattr(self, "use_disk", False)

        # fetch headers to retrieve size and type
        try:
            _, self.headers = stream_file(
                url, byte_stream=io.BytesIO(), only_first_block=True
            )
        except Exception as exc:
            raise OSError(f"Unable to access URL at {url}: {exc}") from None

        # HTML content will be indexed.
        # we proxy the content in the Item to prevent double-download of the resource
        # we use a value-variable to prevent race-conditions in the multiple
        # reads of the content in the provider
        if self.should_index:
            self.fileobj = io.BytesIO()
            self.size, _ = stream_file(self.url.geturl(), byte_stream=self.fileobj)
            return

        try:
            # Encoded data (compressed) prevents us from using Content-Length header
            # as source for the content (it represents length of compressed data)
            if self.headers.get("Content-Encoding", "identity") != "identity":
                raise ValueError("Can't trust Content-Length for size")
            # non-html, non-compressed data.
            self.size = int(self.headers["Content-Length"])
        except Exception:
            # we couldn't retrieve size so we have to download resource to
            target, self.size = self.download_for_size(
                self.url, on_disk=use_disk_set, tmp_dir=getattr(self, "tmp_dir", None)
            )
            # downloaded to disk and using a file path from now on
            if use_disk:
                self.filepath = target
            # downloaded to RAM and using a bytes object
            else:
                self.fileobj = target

    def get_path(self) -> str:
        return getattr(self, "path", re.sub(r"^/", "", self.url.path))

    def get_title(self) -> str:
        return getattr(self, "title", "")

    def get_mimetype(self) -> str:
        return getattr(
            self,
            "mimetype",
            self.headers.get("Content-Type", "application/octet-stream"),
        )

    def get_contentprovider(self):
        try:
            return super().get_contentprovider()
        except NotImplementedError:
            return URLProvider(
                url=self.url.geturl(), size=getattr(self, "size", None), ref=self
            )
