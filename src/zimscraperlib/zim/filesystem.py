#!/usr/bin/env python
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

from __future__ import annotations

import datetime
import pathlib
import re
import tempfile
from collections.abc import Sequence

from zimscraperlib import logger
from zimscraperlib.filesystem import get_file_mimetype
from zimscraperlib.html import find_title_in_file
from zimscraperlib.types import get_mime_for_name
from zimscraperlib.zim.creator import Creator
from zimscraperlib.zim.items import StaticItem


class FileItem(StaticItem):
    """libzim.writer.Article reflecting a local file within a root folder"""

    def __init__(
        self,
        root: pathlib.Path,
        filepath: pathlib.Path,
    ):
        super().__init__()
        self.root = root
        self.filepath = filepath
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
    redirects: Sequence[tuple[str, str, str | None]] | None = None,
    redirects_file: pathlib.Path | None = None,
):
    """add redirects from list of source/target or redirects file to zim"""
    if redirects is None:
        redirects = []
    for source_url, target_url, title in redirects:
        zim_file.add_redirect(source_url, target_url, title)

    if redirects_file:
        with open(redirects_file) as fh:
            for line in fh.readlines():
                namespace, path, title, target_url = re.match(
                    r"^(.)\t(.+)\t(.*)\t(.+)$", line
                ).groups()  # pyright: ignore
                if namespace.strip():
                    path = f"{namespace.strip()}/{path}"
                zim_file.add_redirect(path, target_url, title)


def make_zim_file(
    build_dir: pathlib.Path,
    fpath: pathlib.Path,
    name: str,
    main_page: str,
    illustration: str,
    title: str,
    description: str,
    date: datetime.date = None,  # noqa: RUF013  # pyright: ignore
    language: str = "eng",
    creator: str = "-",
    publisher="-",
    tags: Sequence[str] = None,  # noqa: RUF013  # pyright: ignore
    source: str = None,  # noqa: RUF013  # pyright: ignore
    flavour: str = None,  # noqa: RUF013  # pyright: ignore
    scraper: str = None,  # noqa: RUF013  # pyright: ignore
    long_description: str = None,  # noqa: RUF013  # pyright: ignore
    without_fulltext_index: bool = False,  # noqa: FBT001, FBT002, ARG001
    redirects: Sequence[tuple[str, str, str]] = None,  # noqa: RUF013  # pyright: ignore
    redirects_file: pathlib.Path = None,  # noqa: RUF013  # pyright: ignore
    rewrite_links: bool = True,  # noqa: FBT001, FBT002, ARG001
    workaround_nocancel: bool = True,  # noqa: FBT001, FBT002
    ignore_duplicates: bool = True,  # noqa: FBT001, FBT002
    disable_metadata_checks: bool = False,  # noqa: FBT001, FBT002
):
    """Creates a zimwriterfs-like ZIM file at {fpath} from {build_dir}

    main_page: path of item to serve as main page
    illustration: relative path to illustration file in build_dir
    tags: list of str tags to add to meta
    redirects: list of (src, dst, title) tuple to create redirects from
    rewrite_links controls whether to rewrite HTML/CSS content
      -> add namespaces to relative links
    workaround_nocancel: disable workaround to prevent ZIM creation on error"""

    # sanity checks
    if not build_dir.exists() or not build_dir.is_dir():
        raise OSError(f"Incorrect build_dir: {build_dir}")

    illustration_path = build_dir / illustration
    if not illustration_path.exists() or not illustration_path.is_file():
        raise OSError(f"Incorrect illustration: {illustration} ({illustration_path})")

    with open(illustration_path, "rb") as fh:
        illustration_data = fh.read()

    zim_file = Creator(
        filename=fpath,
        main_path=main_page,
        ignore_duplicates=ignore_duplicates,
        disable_metadata_checks=disable_metadata_checks,
    ).config_metadata(
        **{
            k: v
            for k, v in {
                # (somewhat) mandatory
                "Name": name,
                "Title": title,
                "Description": description,
                "Date": date or datetime.date.today(),  # noqa: DTZ011
                "Language": language,
                "Creator": creator,
                "Publisher": publisher,
                # optional
                "Tags": ";".join(tags) if tags else None,
                "Source": source,
                "Flavour": flavour,
                "Scraper": scraper,
                "LongDescription": long_description,
                "Illustration_48x48_at_1": illustration_data,
            }.items()
            if v is not None
        }
    )

    zim_file.start()
    try:
        logger.debug(f"Preparing zimfile at {zim_file.filename}")

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


class IncorrectZIMPathError(Exception):
    """A generic exception for any problem encountered in validate_zimfile_creatable"""

    pass


class MissingZIMFolderError(IncorrectZIMPathError):
    """Exception raised in validate_zimfile_creatable when folder does not exists"""

    pass


class NotADirectoryZIMFolderError(IncorrectZIMPathError):
    """Exception raised in validate_zimfile_creatable when folder is not a directory"""

    pass


class NotWritableZIMFolderError(IncorrectZIMPathError):
    """Exception raised in validate_zimfile_creatable when folder is not writable"""

    pass


class IncorrectZIMFilenameError(IncorrectZIMPathError):
    """
    Exception raised in validate_zimfile_creatable when filename is not creatable

    This usually occurs when bad characters are present in filename (typically
    characters not supported on current filesystem).
    """

    pass


def validate_zimfile_creatable(folder: str | pathlib.Path, filename: str):
    """Validate that a ZIM can be created in given folder with given filename

    Any problem encountered raises an exception inheriting from IncorrectZIMPathError

    Checks that:
    - folder passed exists (or raise MissingZIMFolderError exception)
    - folder passed is a directory (or raise NotADirectoryZIMFolderError exception)
    - folder is writable, i.e. it is possible to create a file in folder (or raise
    NotWritableZIMFolderError exception with inner exception details)
    - filename is creatable, i.e. there is no bad characters in filename (or raise
    IncorrectZIMFilenameError exception with inner exception details)
    """
    folder = pathlib.Path(folder)

    # ensure folder exists
    if not folder.exists():
        raise MissingZIMFolderError(
            f"Folder to create the ZIM does not exist: {folder}"
        )

    # ensure folder is a directory
    if not folder.is_dir():
        raise NotADirectoryZIMFolderError(
            f"Folder to create the ZIM is not a directory: {folder}"
        )

    logger.debug(f"Attempting to confirm output is writable in directory {folder}")

    try:
        # ensure folder is writable
        with tempfile.NamedTemporaryFile(dir=folder, delete=True) as fh:
            logger.debug(f"Output is writable. Temporary file used for test: {fh.name}")
    except Exception as exc:
        raise NotWritableZIMFolderError(
            f"Folder to create the ZIM is not writable: {folder}"
        ) from exc

    # ensure ZIM file is creatable with the given name
    fpath = folder / filename
    try:
        logger.debug(f"Confirming ZIM file can be created at {fpath}")
        fpath.touch()
        fpath.unlink()
    except Exception as exc:
        raise IncorrectZIMFilenameError(
            f"ZIM filename is not creatable: {fpath}"
        ) from exc
