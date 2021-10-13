#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

""" zimwriterfs-like tools to convert a build folder into a ZIM

    make_zim_file behaves in a similar way to zimwriterfs and expects the same options:

    - Guesses file mime-type from filenames
    - Add all files to respective namespaces based on mime type
    - Add redirects from a zimwriterfs-compatible redirects TSV
    - Adds common metadata

    Also included:
    - Add redirect from a list of (source, destination, title) strings

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

import datetime
import pathlib
import re
from typing import Optional, Sequence, Tuple

from .. import logger
from ..filesystem import get_file_mimetype
from ..html import find_title_in_file
from ..types import get_mime_for_name
from .creator import Creator
from .items import StaticItem


class FileItem(StaticItem):
    """libzim.writer.Article reflecting a local file within a root folder"""

    def __init__(
        self,
        root: pathlib.Path,
        filepath: pathlib.Path,
    ):
        super().__init__(root=root, filepath=filepath)
        # first look inside the file's magic headers
        self.mimetype = get_file_mimetype(self.filepath)
        # most web-specific files are plain text. In this case, use extension
        if self.mimetype.startswith("text/"):
            self.mimetype = get_mime_for_name(self.filepath)

    def get_path(self) -> str:
        return str(self.filepath.relative_to(self.root))

    def get_title(self) -> str:
        return find_title_in_file(self.filepath, self.mimetype)


def add_to_zim(
    root: pathlib.Path,
    zim_file: Creator,
    fpath: pathlib.Path,
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
            add_to_zim(root, zim_file, leaf)
    else:
        logger.debug(f".. [FILE] {fpath}")
        zim_file.add_item(FileItem(root, fpath))


def add_redirects_to_zim(
    zim_file: Creator,
    redirects: Optional[Sequence[Tuple[str, str, Optional[str]]]] = None,
    redirects_file: Optional[pathlib.Path] = None,
):
    """add redirects from list of source/target or redirects file to zim"""
    if redirects is None:
        redirects = []
    for source_url, target_url, title in redirects:
        zim_file.add_redirect(source_url, target_url, title)

    if redirects_file:
        with open(redirects_file, "r") as fh:
            for line in fh.readlines():
                namespace, path, title, target_url = re.match(
                    r"^(.)\t(.+)\t(.*)\t(.+)$", line
                ).groups()
                if namespace.strip():
                    path = f"{namespace.strip()}/{path}"
                zim_file.add_redirect(path, target_url, title)


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

    main_page: path of item to serve as main page
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
        filename=fpath,
        main_path=main_page,
        index_language="" if without_fulltext_index else language,
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
        },
    )

    zim_file.start()
    try:
        logger.debug(f"Preparing zimfile at {zim_file.filename}")

        # add favicon as illustration
        with open(favicon_path, "rb") as fh:
            zim_file.add_default_illustration(fh.read())

        # recursively add content from build_dir
        logger.debug(f"Recursively adding files from {build_dir}")
        add_to_zim(build_dir, zim_file, build_dir)

        if redirects or redirects_file:
            logger.debug("Creating redirects")
            add_redirects_to_zim(
                zim_file, redirects=redirects, redirects_file=redirects_file
            )

    # prevents .finish() which would create an incomplete .zim file
    # this would leave a .zim.tmp folder behind.
    # UPSTREAM: wait until a proper cancel() is provided
    except Exception:
        if workaround_nocancel:
            zim_file.can_finish = False  # pragma: no cover
        raise
    finally:
        zim_file.finish()
