#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

""" Zim Creator helper

    Convenient subclass of libzim.writer.Creator with:
    - direct method to add an HTML Article from file or content
    - direct method to add a CSS Article from file or content
    - direct method to add binary content (works for any type) from file or content
    - direct method to add redirects
    - prevent exeption on double call to close()
    - optional rewriting of HTML links
    - optional rewriting of URLs in CSS

    Convenient subclass of libzim.writer.Article with:
    - metadata set on initialization
    - metadata stored on object
    - content stored on object
    - can be used to store a filepath and content read from it (not stored)

    Convenient suclass of libzim.writer.Article for Redirects """

import pathlib
import datetime
from typing import Callable, Dict, Union, Optional

import libzim.writer

from ..types import ARTICLE_MIME
from ..filesystem import get_content_mimetype, get_file_mimetype
from .rewriting import (
    find_namespace_for,
    fix_links_in_html,
    fix_urls_in_css,
    to_longurl,
)


class StaticArticle(libzim.writer.Article):
    """libzim.writer.Article holding it's data (except content when using filename)

    Easy shortcut to subclassing Article when data's already at hand.
    `content` can be set (bytes); then stored in object and returned on get_data()
    If `filename` is set, get_data() returns it's content"""

    def __init__(self, **kwargs: Dict[str, Union[str, bool, bytes]]):
        super().__init__()
        for k, v in kwargs.items():
            setattr(self, k, v)

    def get_url(self) -> str:
        return getattr(self, "url", "")

    def get_title(self) -> str:
        return getattr(self, "title", "")

    def is_redirect(self) -> bool:
        return getattr(self, "redirect_url", None) is not None

    def get_mime_type(self) -> str:
        return getattr(self, "mime_type", "")

    def get_filename(self) -> str:
        return getattr(self, "filename", "")

    def should_compress(self) -> bool:
        return getattr(self, "compress", False)

    def should_index(self) -> bool:
        return getattr(self, "index", False)

    def get_redirect_url(self) -> str:
        return getattr(self, "redirect_url", "")

    def get_data(self) -> bytes:
        if self.get_filename():
            with open(self.get_filename(), "rb") as fh:
                return libzim.writer.Blob(fh.read())
        return libzim.writer.Blob(getattr(self, "content", b""))


class RedirectArticle(libzim.writer.Article):
    """ libzim.writer.Article representing a simple from/to redirect """

    def __init__(self, longurl: str, redirect_url: str, title: Optional[str] = ""):
        self.longurl = longurl
        self.redirect_url = redirect_url
        self.title = title

    def get_url(self) -> str:
        return self.longurl

    def get_title(self) -> str:
        return self.title

    def is_redirect(self) -> bool:
        return True

    def should_index(self) -> bool:
        return bool(self.title)

    def get_redirect_url(self) -> str:
        return self.redirect_url


class Creator(libzim.writer.Creator):

    """libzim.writer.Creator subclass

    Note: due to the lack of a cancel() method in the libzim itself, it is not possible
    to stop a zim creation process. Should an error occur in your code, a Zim file
    with up-to-that-moment content will be created at destination.

    To prevent this (creating an unwanted Zim file) from happening,
    a workaround is in place. It prevents the libzim from finishing its process.
    While it results in no Zim file being created, it also results in
    the zim temp folder to be left on disk and very frequently leads to
    a segmentation fault at garbage collection (on exit mostly).

    Meaning you should exit right after an exception in your code (during zim creation)
    Use workaround_nocancel=False to disable the workaround."""

    def __init__(
        self,
        filename: pathlib.Path,
        main_page: str,
        language: Optional[str] = "eng",
        workaround_nocancel: Optional[bool] = True,
        min_chunk_size: Optional[int] = None,
        **metadata: Dict[str, Union[str, datetime.date, datetime.datetime]]
    ):
        super().__init__(
            filename=filename,
            main_page=main_page,
            index_language=language,
            **{"min_chunk_size": min_chunk_size} if min_chunk_size is not None else {}
        )
        self.update_metadata(**metadata)
        self.workaround_nocancel = workaround_nocancel

    def add_zim_article(self, article: libzim.writer.Article):
        """ Add a libzim.writer Article """
        try:
            super().add_article(article)
        except Exception:
            if self.workaround_nocancel:
                self._closed = True  # pragma: no cover
            raise

    def add_binary(
        self,
        url: str,
        fpath: Optional[pathlib.Path] = None,
        content: Optional[bytes] = None,
        namespace: Optional[str] = None,
        mime_type: Optional[str] = None,
        should_compress: Optional[bool] = False,
        should_index: Optional[bool] = False,
    ):
        """Add a File or conent at a specified url and get its longurl

        mime_type is retrieved from content (magic) if not specified
        namespace is computed from mime_type if not specified

        Content specified either from content (str|bytes) arg or read from fpath
        Source file can be safely deleted after this call."""
        if fpath is None and content is None:
            raise ValueError("One of fpath or content is required")

        if not mime_type:
            mime_type = (
                get_file_mimetype(fpath) if fpath else get_content_mimetype(content[:8])
            )
        if not namespace:
            namespace = find_namespace_for(mime_type)
        self.add_zim_article(
            StaticArticle(
                url=to_longurl(namespace, url),
                mime_type=mime_type,
                filename=str(fpath) if fpath is not None else "",
                content=content,
                index=should_index,
                compress=should_compress,
            )
        )
        return to_longurl(namespace, url)

    def add_article(
        self,
        url: str,
        title: str,
        fpath: Optional[pathlib.Path] = None,
        content: Optional[str] = None,
        mime_type: Optional[str] = ARTICLE_MIME,
        should_index: Optional[bool] = True,
        should_compress: Optional[bool] = True,
        rewrite_links: Optional[bool] = False,
    ):
        """Add an HTML file or content into A/ namespace (url is without namespace)

        Saves specifying the namespace and MIME-type and also provides easy access
        to links rewriting and HTML-friendly defaults (compress, index)

        Content specified either from content (str) argument or read from fpath
        Source file can be safely deleted after this call."""

        return self._add_rewriten(
            namespace="A",
            url=url,
            title=title,
            mime_type=mime_type,
            should_index=should_index,
            should_compress=should_compress,
            rewrite_links=rewrite_links,
            rewriter=fix_links_in_html,
            fpath=fpath,
            content=content,
        )

    def add_css(
        self,
        url: str,
        fpath: Optional[pathlib.Path] = None,
        content: Optional[str] = None,
        should_compress: Optional[bool] = True,
        should_index: Optional[bool] = False,
        rewrite_links: Optional[bool] = False,
    ):
        """Add a CSS file or content to - namespace (url is without namespace)

        Saves specifying the namespace and MIME-type and also provides easy access
        to links rewriting and CSS-friendly defaults (compress, no index)

        Content specified either from content (str) argument or read from fpath
        Source file can be safely deleted after this call."""
        return self._add_rewriten(
            namespace="-",
            url=url,
            title="",
            mime_type="text/css",
            should_index=should_index,
            should_compress=should_compress,
            rewrite_links=rewrite_links,
            rewriter=fix_urls_in_css,
            fpath=fpath,
            content=content,
        )

    def _add_rewriten(
        self,
        namespace: str,
        url: str,
        title: str,
        mime_type,
        should_index,
        should_compress,
        rewrite_links,
        rewriter: Callable[[str, str], str],
        fpath: Optional[pathlib.Path] = None,
        content: Optional[str] = None,
    ):
        """Add a text article after rewriting its content with custom rewriter

        Generic function not intended for direct access.

        Allows adding an article while automatically rewriting its content using
        the specified rewriter (text only)

        Content specified either from content (str) argument or read from fpath
        Source file can be safely deleted after this call."""
        if fpath is None and content is None:
            raise ValueError("One of fpath or content is required")
        if fpath and not content:
            with open(fpath, "r") as fh:
                content = fh.read()

        if rewrite_links:
            content = rewriter(to_longurl(namespace, url), content)
        self.add_zim_article(
            StaticArticle(
                url=to_longurl(namespace, url),
                mime_type=mime_type,
                title=title,
                content=content.encode("UTF-8"),
                index=should_index,
                compress=should_compress,
            )
        )
        return to_longurl(namespace, url)

    def add_redirect(self, url: str, redirect_url: str, title: Optional[str] = ""):
        """Add a redirect from (full) url to (full) redirect_url

        Both url and redirect_url should include namespace.
        Cross-namespace redirects are allowed.

        title is optional. when set, the redirect itself
        can be found on suggestions (indexed)"""
        self.add_zim_article(RedirectArticle(url, redirect_url, title))
        return url

    def close(self):
        """ Triggers finalization of ZIM creation and create final ZIM file. """
        try:
            super().close()
        except RuntimeError:
            pass
