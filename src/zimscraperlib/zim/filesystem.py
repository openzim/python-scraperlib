#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

""" zimwriterfs-like tools to convert a build folder into a Zim

    make_zim_file behaves in a similar way to zimwriterfs and expects the same options:

    - Guesses file mime-type from filenames
    - Add all files to respective namespaces based on mime type
    - Rewrites all links in HTML and CSS files
    - Add redirects from a zimwriterfs-compativle redirects TSV
    - Adds common metadata
    - Add a -/favicon redirect to specified favicon

    Also included:
    - Add redirect from a list of (source, destination, title) strings
    - Ability to disable links rewriting (rewrite_links=False)

    Note: due to the lack of a cancel() method in the libzim itself, it is not possible
    to stop a zim creation process. Should an error occur in your code, a Zim file
    with up-to-that-moment content will be created at destination.

    To prevent this (creating an unwanted Zim file) from happening,
    a workaround is in place. It prevents the libzim from finishing its process.
    While it results in no Zim file being created, it results in the zim temp folder
    to be left on disk and very frequently leads to a segmentation fault at garbage
    collection (on exit mostly).

    Meaning you should exit right after an exception in your code (during zim creation)
    Use workaround_nocancel=False to disable the workaround. """

import re
import pathlib
import datetime
from typing import Tuple, Optional, Sequence

import libzim.writer

from .. import logger
from ..filesystem import get_file_mimetype
from ..types import ARTICLE_MIME, get_mime_for_name
from .creator import Creator
from .rewriting import (
    fix_links_in_html_file,
    fix_urls_in_css_file,
    find_url,
    find_title_in_file,
    to_longurl,
)


class FileArticle(libzim.writer.Article):
    """ libzim.writer.Article reflecting a local file within a root folder """

    def __init__(
        self,
        root: pathlib.Path,
        fpath: pathlib.Path,
        rewrite_links: Optional[bool] = False,
    ):
        super().__init__()
        self.root = root
        self.fpath = fpath
        self.rewrite_links = rewrite_links
        # first look inside the file's magic headers
        self.mime_type = get_file_mimetype(self.fpath)
        # most web-specific files are plain text. In this case, use extension
        if self.mime_type.startswith("text/"):
            self.mime_type = get_mime_for_name(self.fpath)

    def get_url(self) -> str:
        return find_url(self.root, self.fpath, self.mime_type)

    def get_title(self) -> str:
        return find_title_in_file(self.fpath, self.mime_type)

    def is_redirect(self) -> bool:
        return False

    def get_mime_type(self) -> str:
        return self.mime_type

    def get_filename(self) -> str:
        return ""

    def should_compress(self) -> bool:
        return self.mime_type.startswith("text/") or self.mime_type in (
            "application/javascript",
            "application/json",
            "image/svg+xml",
        )

    def should_index(self) -> bool:
        return self.mime_type == ARTICLE_MIME

    def get_redirect_url(self) -> str:
        raise NotImplementedError

    def get_data(self) -> libzim.writer.Blob:
        if self.rewrite_links:
            mime = self.get_mime_type()
            if mime in (ARTICLE_MIME, "text/css"):
                rewriter = (
                    fix_links_in_html_file
                    if mime == ARTICLE_MIME
                    else fix_urls_in_css_file
                )
                return libzim.writer.Blob(
                    rewriter(self.fpath, root=self.root).encode("utf-8")
                )
        with open(self.fpath, "rb") as fh:
            return libzim.writer.Blob(fh.read())


class FaviconArticle(FileArticle):
    """-/favicon is an expected Article that'd be a redirect to a real image

    Instanciate it with root foler and fpath of the actual image"""

    def get_url(self) -> str:
        return "-/favicon"

    def get_title(self) -> str:
        return ""

    def is_redirect(self) -> bool:
        return True

    def get_mime_type(self) -> str:
        return ""

    def get_redirect_url(self) -> str:
        return find_url(self.root, self.fpath, get_file_mimetype(self.fpath))

    def get_data(self) -> str:
        return ""


def add_to_zim(
    root: pathlib.Path,
    zim_file: Creator,
    fpath: pathlib.Path,
    rewrite_links: Optional[bool],
):
    """recursively add a path to a zim file

    root:
        main folder containing all content
    zim_file:
        zim Creator
    fpath:
        path to the file/folder to add to the ZIM
    rewrite_links:
        whether HTML and CSS files should have their links fixed for namespaces"""
    if fpath.is_dir():
        logger.debug(f".. [DIR] {fpath}")
        for leaf in fpath.iterdir():
            logger.debug(f"... [FILE] {leaf}")
            add_to_zim(root, zim_file, leaf, rewrite_links)
    else:
        logger.debug(f".. [FILE] {fpath}")
        art = FileArticle(root, fpath, rewrite_links)
        zim_file.add_zim_article(art)


def add_redirects_to_zim(
    zim_file: Creator,
    redirects: Optional[Sequence[Tuple[str, str, Optional[str]]]] = None,
    redirects_file: Optional[pathlib.Path] = None,
):
    """ add redirects from list of source/target or redirects file to zim """
    if redirects is None:
        redirects = []
    for source_url, target_url, title in redirects:
        zim_file.add_redirect(source_url, target_url, title)

    if redirects_file:
        with open(redirects_file, "r") as fh:
            for line in fh.readlines():
                namespace, url, title, target_url = re.match(
                    r"^(.)\t(.+)\t(.*)\t(.+)$", line
                ).groups()
                zim_file.add_redirect(to_longurl(namespace, url), target_url, title)


def make_zim_file(
    build_dir: pathlib.Path,
    fpath: pathlib.Path,
    name: str,
    main_page: str,
    favicon: str,
    title: str,
    description: str,
    date: datetime.date = None,
    language: str = "eng",
    creator: str = "-",
    publisher="-",
    tags: Sequence[str] = None,
    source: str = None,
    flavour: str = None,
    scraper: str = None,
    without_fulltext_index: bool = False,
    redirects: Sequence[Tuple[str, str, str]] = None,
    redirects_file: pathlib.Path = None,
    rewrite_links: bool = True,
    workaround_nocancel: bool = True,
):
    """Creates a zimwriterfs-like ZIM file at {fpath} from {build_dir}

    main_page: url (without A/ ns) or article to serve as main_page (must be in A/)
    favicon: relative path to favicon file in build_dir
    tags: list of str tags to add to meta
    redirects: list of (src, dst, title) tuple to create redirects from
    rewrite_links controls whether to rewrite HTML/CSS content
      -> add namespaces to relative links
    workaround_nocancel: disable workaround to prevent ZIM creation on error"""

    # sanity checks
    if not build_dir.exists() or not build_dir.is_dir():
        raise IOError(f"Incorrect build_dir: {build_dir}")

    favicon_path = build_dir / favicon
    if not favicon_path.exists() or not favicon_path.is_file():
        raise IOError(f"Incorrect favicon: {favicon} ({favicon_path})")

    zim_file = Creator(
        fpath,
        main_page=main_page,
        index_language="" if without_fulltext_index else language,
    )
    try:
        logger.debug(f"Preparing zimfile at {zim_file.filename}")
        # set metadata
        logger.debug(f"Recording metadata")
        zim_file.update_metadata(
            **{
                k: v
                for k, v in {
                    # (somewhat) mandatory
                    "name": name,
                    "title": title,
                    "description": description,
                    "date": date or datetime.date.today(),
                    "language": language,
                    "creator": creator,
                    "publisher": publisher,
                    # optional
                    "tags": ";".join(tags) if tags else None,
                    "source": source,
                    "flavour": flavour,
                    "scraper": scraper,
                }.items()
                if v is not None
            }
        )

        # add favicon redirect
        logger.debug(f"Adding favicon from {favicon}")
        zim_file.add_zim_article(FaviconArticle(build_dir, favicon_path))

        # recursively add content from build_dir
        logger.debug(f"Recursively adding files from {build_dir}")
        add_to_zim(build_dir, zim_file, build_dir, rewrite_links)

        if redirects or redirects_file:
            logger.debug(f"Creating redirects")
            add_redirects_to_zim(
                zim_file, redirects=redirects, redirects_file=redirects_file
            )

    # prevents .close() on __del__ which would create an incomplete .zim file
    # this would leave a .zim.tmp folder behind.
    # UPSTREAM: wait until a proper cancel() is provided
    except Exception:
        if workaround_nocancel:
            zim_file._closed = True  # pragma: no cover
        raise
    finally:
        zim_file.close()
