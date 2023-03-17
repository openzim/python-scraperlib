#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

""" ZIM Creator helper

    Convenient subclass of libzim.writer.Creator with:
    - easier configuration of commonly set props during init
    - start/stop methods to bypass the contextmanager
    - method to create an entry directly from args
    - direct method to add redirects without title
    - prevent exeption on double call to close()

    Convenient subclasses of libzim.writer.Item with:
    - metadata set on initialization
    - metadata stored on object
    Sister subclass StaticItem (inheriting from it) with:
    - content stored on object
    - can be used to store a filepath and content read from it (not stored) """

import datetime
import pathlib
import re
import weakref
from typing import Any, Callable, Iterable, Optional, Tuple, Union

import libzim.writer

from ..constants import (
    DEFAULT_DEV_ZIM_METADATA,
    FRONT_ARTICLE_MIMETYPES,
    MANDATORY_ZIM_METADATA_KEYS,
)
from ..filesystem import delete_callback, get_content_mimetype, get_file_mimetype
from ..i18n import is_valid_iso_639_3
from ..types import get_mime_for_name
from .items import StaticItem
from .metadata import (
    validate_counter,
    validate_date,
    validate_description,
    validate_illustrations,
    validate_language,
    validate_longdescription,
    validate_required_values,
    validate_standard_str_types,
    validate_tags,
    validate_title,
)

DUPLICATE_EXC_STR = re.compile(
    r"^Impossible to add(.+)"
    r"dirent\'s title to add is(.+)"
    r"existing dirent's title is(.+)",
    re.MULTILINE | re.DOTALL,
)


def mimetype_for(
    path: str,
    content: Optional[Union[bytes, str]] = None,
    fpath: Optional[pathlib.Path] = None,
    mimetype: Optional[str] = None,
) -> str:
    """mimetype as provided or guessed from fpath, path or content"""
    if not mimetype:
        mimetype = (
            get_file_mimetype(fpath) if fpath else get_content_mimetype(content[:2048])
        )
        # try to guess more-defined mime if it's text
        if (
            not mimetype
            or mimetype == "application/octet-stream"
            or mimetype.startswith("text/")
        ):
            mimetype = get_mime_for_name(fpath if fpath else path, mimetype, mimetype)
    return mimetype


class Creator(libzim.writer.Creator):

    """libzim.writer.Creator subclass

    Note: due to the lack of a cancel() method in the libzim itself, it is not possible
    to stop a zim creation process. Should an error occur in your code, a Zim file
    with up-to-that-moment content will be created at destination.

    To prevent this (creating an unwanted ZIM file) from happening,
    a workaround is in place. It prevents the libzim from finishing its process.
    While it results in no ZIM file being created, it also results in
    the zim temp folder to be left on disk and very frequently leads to
    a segmentation fault at garbage collection (on exit mostly).

    Meaning you should exit right after an exception in your code (during zim creation)
    Use workaround_nocancel=False to disable the workaround."""

    def __init__(
        self,
        filename: pathlib.Path,
        main_path: str,
        compression: Optional[str] = None,
        workaround_nocancel: Optional[bool] = True,
        ignore_duplicates: Optional[bool] = False,
    ):
        super().__init__(filename=filename)
        self._metadata = dict()
        self.__indexing_configured = False
        self.can_finish = True

        self.set_mainpath(main_path)

        if compression:
            self.config_compression(
                getattr(libzim.writer.Compression, compression.lower())
                if isinstance(compression, str)
                else compression
            )

        self.workaround_nocancel = workaround_nocancel
        self.ignore_duplicates = ignore_duplicates

    def config_indexing(self, indexing: bool, language: Optional[str] = None):
        """Toggle full-text and title indexing of entries

        Uses Language metadata's value (or "") if not set"""
        language = language or self._metadata.get("Language", "")
        if indexing and not is_valid_iso_639_3(language):
            raise ValueError("Not a valid ISO-639-3 language code")
        super().config_indexing(indexing, language)
        self.__indexing_configured = True
        return self

    def start(self):
        if not all([self._metadata.get(key) for key in MANDATORY_ZIM_METADATA_KEYS]):
            raise ValueError("Mandatory metadata are not all set.")

        for name, value in self._metadata.items():
            if value:
                self.validate_metadata(name, value)

        language = self._metadata.get("Language", "").split(",")
        if language[0] and not self.__indexing_configured:
            self.config_indexing(True, language[0])

        super().__enter__()

        self.add_illustration(48, self._metadata["Illustration_48x48@1"])
        del self._metadata["Illustration_48x48@1"]
        for name, value in self._metadata.items():
            if value:
                self.add_metadata(name, value)

        return self

    def validate_metadata(
        self,
        name: str,
        value: Union[bytes, str, datetime.datetime, datetime.date, Iterable[str]],
    ):
        """Ensures metadata value for name is conform with the openZIM spec on Metadata

        Also enforces recommendations
        See https://wiki.openzim.org/wiki/Metadata"""

        validate_required_values(name, value)
        validate_standard_str_types(name, value)

        validate_title(name, value)
        validate_date(name, value)
        validate_language(name, value)
        validate_counter(name, value)
        validate_description(name, value)
        validate_longdescription(name, value)
        validate_tags(name, value)
        validate_illustrations(name, value)

    def add_metadata(
        self,
        name: str,
        content: Union[str, bytes, datetime.date, datetime.datetime],
        mimetype: str = "text/plain;charset=UTF-8",
    ):
        self.validate_metadata(name, content)
        super().add_metadata(name, content, mimetype)

    def config_metadata(
        self,
        *,
        Name: str,
        Language: str,
        Title: str,
        Description: str,
        LongDescription: Optional[str] = None,
        Creator: str,
        Publisher: str,
        Date: Union[datetime.datetime, datetime.date, str],
        Illustration_48x48_at_1: bytes,
        Tags: Optional[Union[Iterable[str], str]] = None,
        Scraper: Optional[str] = None,
        Flavour: Optional[str] = None,
        Source: Optional[str] = None,
        License: Optional[str] = None,
        Relation: Optional[str] = None,
        **extras: str,
    ):
        """Sets all mandatory Metadata as well as standard and any other text ones"""
        self._metadata.update(
            {
                "Name": Name,
                "Title": Title,
                "Creator": Creator,
                "Publisher": Publisher,
                "Date": Date,
                "Description": Description,
                "Language": Language,
                "License": License,
                "LongDescription": LongDescription,
                "Tags": Tags,
                "Relation": Relation,
                "Flavour": Flavour,
                "Source": Source,
                "Scraper": Scraper,
                "Illustration_48x48@1": Illustration_48x48_at_1,
            }
        )
        self._metadata.update(extras)
        return self

    def config_dev_metadata(self, **extras: str):
        """Calls config_metadata with default (yet overridable) values for dev"""
        devel_default_metadata = DEFAULT_DEV_ZIM_METADATA.copy()
        devel_default_metadata.update(extras)
        return self.config_metadata(**devel_default_metadata)

    def add_item_for(
        self,
        path: str,
        title: Optional[str] = None,
        fpath: Optional[pathlib.Path] = None,
        content: Optional[bytes] = None,
        mimetype: Optional[str] = None,
        is_front: Optional[bool] = None,
        should_compress: Optional[bool] = None,
        delete_fpath: Optional[bool] = False,
        duplicate_ok: Optional[bool] = None,
        callback: Optional[Union[callable, Tuple[callable, Any]]] = None,
    ):
        """Add a File or content at a specified path and get its path

        mimetype is retrieved from content (magic) if not specified
        if magic finds it to be text/*, guesses the mimetype from the source
        filename (if using a file) or the destination path

        is_front: whether this Item is a FRONT_ARTICLE or not. Those are considered
        user-facing Entries and thus part of suggestion, random, etc.
        Default (not set) sets it based on mimetype (see constants for list)

        should_compress: specify whether this Item should be compressed or not.
        Default (not set) lets the libzim decide (based on mimetype)

        Content specified either from content (str|bytes) arg or read from fpath
        Source file can be safely deleted after this call.

        callback: see add_item()"""
        if fpath is None and content is None:
            raise ValueError("One of fpath or content is required")

        mimetype = mimetype_for(
            path=path, content=content, fpath=fpath, mimetype=mimetype
        )

        if is_front is None:
            is_front = mimetype in FRONT_ARTICLE_MIMETYPES
        hints = {libzim.writer.Hint.FRONT_ARTICLE: is_front}

        if should_compress is not None:
            hints[libzim.writer.Hint.COMPRESS] = should_compress

        kwargs = {
            "path": path,
            "title": title or "",
            "mimetype": mimetype,
            "filepath": fpath if fpath is not None else "",
            "hints": hints,
            "content": content,
        }
        if delete_fpath and fpath:
            cb = [delete_callback, fpath]
            if callback and callable(callback):
                cb.append(callback)
            elif callback:
                cb += list(callback)
            callback = tuple(cb)

        self.add_item(
            StaticItem(**kwargs), callback=callback, duplicate_ok=duplicate_ok
        )
        return path

    def add_item(
        self,
        item: libzim.writer.Item,
        duplicate_ok: Optional[bool] = None,
        callback: Optional[Union[Callable, Tuple[Callable, Any]]] = None,
    ):
        """Add a libzim.writer.Item

        callback: either a single callable or a tuple containing the callable
        as first element then the arguments to pass to the callable.
        Note: you must __not__ include the item itself in those arguments."""
        if callback:
            if callable(callback):
                weakref.finalize(item, callback)
            else:
                weakref.finalize(item, *callback)

        duplicate_ok = duplicate_ok or self.ignore_duplicates
        try:
            try:
                super().add_item(item)
            except RuntimeError as exc:
                if not DUPLICATE_EXC_STR.match(str(exc)) or not duplicate_ok:
                    raise exc
        except Exception:
            if self.workaround_nocancel:
                self.can_finish = False  # pragma: no cover
            raise

    def add_redirect(
        self,
        path: str,
        target_path: str,
        title: Optional[str] = "",
        is_front: Optional[bool] = None,
        duplicate_ok: Optional[bool] = None,
    ):
        """Add a redirect from path to target_path

        title is optional. when set, the redirect itself
        can be found on suggestions (indexed) if considered FRONT_ARTICLE"""
        hints = {}
        if is_front is not None:
            hints[libzim.writer.Hint.FRONT_ARTICLE] = bool(is_front)

        duplicate_ok = duplicate_ok or self.ignore_duplicates

        try:
            try:
                super().add_redirection(path, title, target_path, hints)
            except RuntimeError as exc:
                if not DUPLICATE_EXC_STR.match(str(exc)) or not duplicate_ok:
                    raise exc
        except Exception:
            if self.workaround_nocancel:
                self.can_finish = False  # pragma: no cover
            raise

    def finish(self, exc_type=None, exc_val=None, exc_tb=None):
        """Triggers finalization of ZIM creation and create final ZIM file."""
        if not getattr(self, "can_finish", False):
            return
        try:
            super().__exit__(None, None, None)
        except RuntimeError:
            pass

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.finish(exc_type, exc_val, exc_tb)
