#!/usr/bin/env python
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

from __future__ import annotations

import io
import logging
import pathlib
import re
import weakref
from collections.abc import Callable
from typing import Any

import libzim.writer  # pyright: ignore
import PIL.Image

import zimscraperlib.zim.metadata
from zimscraperlib import logger
from zimscraperlib.constants import FRONT_ARTICLE_MIMETYPES
from zimscraperlib.filesystem import (
    delete_callback,
    get_content_mimetype,
    get_file_mimetype,
)
from zimscraperlib.i18n import is_valid_iso_639_3
from zimscraperlib.types import get_mime_for_name
from zimscraperlib.zim.indexing import IndexData
from zimscraperlib.zim.items import StaticItem
from zimscraperlib.zim.metadata import (
    DEFAULT_DEV_ZIM_METADATA,
    MANDATORY_ZIM_METADATA_KEYS,
    IllustrationMetadata,
    LanguageMetadata,
    Metadata,
    StandardMetadataList,
)

DUPLICATE_EXC_STR = re.compile(
    r"^Impossible to add(.+)"
    r"dirent\'s title to add is(.+)"
    r"existing dirent's title is(.+)",
    re.MULTILINE | re.DOTALL,
)


def mimetype_for(
    path: str,
    content: bytes | str | None = None,
    fpath: pathlib.Path | None = None,
    mimetype: str | None = None,
) -> str | None:
    """mimetype as provided or guessed from fpath, path or content"""
    if not mimetype:
        mimetype = (
            get_file_mimetype(fpath)
            if fpath
            else get_content_mimetype(content[:2048]) if content else None
        )
        # try to guess more-defined mime if it's text
        if (
            not mimetype
            or mimetype == "application/octet-stream"
            or mimetype.startswith("text/")
        ):
            mimetype = get_mime_for_name(
                filename=fpath if fpath else path, fallback=mimetype, no_ext_to=mimetype
            )
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
    Use workaround_nocancel=False to disable the workaround.

    By default, all metadata are validated for compliance with openZIM guidelines and
    conventions. Set disable_metadata_checks=True to disable this validation (you can
    still do checks manually with the validation methods or your own logic). Metadata
    are anyway still checked to be str or bytes before being passed to the libzim.
    """

    def __init__(
        self,
        filename: pathlib.Path,
        main_path: str,
        compression: str | None = None,
        *,
        workaround_nocancel: bool | None = True,
        ignore_duplicates: bool | None = False,
        check_metadata_conventions: bool = True,
    ):
        super().__init__(filename=filename)
        self._metadata: dict[str, Metadata] = {}
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
        zimscraperlib.zim.metadata.check_metadata_conventions = (
            check_metadata_conventions
        )

    def config_indexing(
        self, indexing: bool, language: str | None = None  # noqa: FBT001
    ):
        """Toggle full-text and title indexing of entries

        Uses Language metadata's value (or "") if not set"""
        language = language or self._get_first_language_metadata_value() or ""
        if indexing and not is_valid_iso_639_3(language):
            raise ValueError("Not a valid ISO-639-3 language code")
        super().config_indexing(indexing, language)
        self.__indexing_configured = True
        return self

    def _log_metadata(self):
        """Log in DEBUG level all metadata key and value"""
        for name, metadata in sorted(self._metadata.items()):

            if metadata is None:
                logger.debug(f"Metadata: {name} is None")
                continue

            if not hasattr(metadata, "value"):
                logger.debug(
                    f"Metadata: {name} is improper metadata type: "
                    f"{metadata.__class__}"
                )
                continue

            # illustration mandates an Image
            if re.match(r"^Illustration_(\d+)x(\d+)@(\d+)$", name):
                try:
                    with PIL.Image.open(io.BytesIO(metadata.libzim_value)) as img:
                        logger.debug(
                            f"Metadata: {name} is a {len(metadata.libzim_value)} bytes "
                            f"{img.size[0]}x{img.size[1]}px {img.format} Image"
                        )
                        continue
                except Exception:  # noqa: S110
                    pass

            # bytes are either encoded string or arbitrary data
            if isinstance(metadata.value, bytes | io.BytesIO):
                raw_value = (
                    metadata.value
                    if isinstance(metadata.value, bytes)
                    else metadata.value.getvalue()
                )
                mimetype = get_content_mimetype(raw_value[:64])
                if not mimetype.startswith("text/"):
                    logger.debug(
                        f"Metadata: {name} is a {len(raw_value)} bytes {mimetype} blob"
                    )
                    continue
                try:
                    logger.debug(f"Metadata: {name} = {raw_value.decode('UTF-8')}")
                except Exception:
                    logger.debug(
                        f"Metadata: {name} is a {len(raw_value)} bytes {mimetype} blob "
                        "not decodable as an UTF-8 string"
                    )
                continue

            # rest is either printable or unexpected
            try:
                logger.debug(f"Metadata: {name} = {metadata.value!s}")
            except Exception:
                logger.debug(
                    f"Metadata: {name} is unexpected data type: "
                    f"{type(metadata.value).__name__}"
                )

    def _get_first_language_metadata_value(self) -> str | None:
        for metadata in self._metadata.values():
            if isinstance(metadata, LanguageMetadata):
                return metadata.libzim_value.decode().split(",")[0]
        return None

    def start(self):
        if logger.isEnabledFor(logging.DEBUG):  # pragma: no cover
            self._log_metadata()

        if not all(self._metadata.get(key) for key in MANDATORY_ZIM_METADATA_KEYS):
            missing_keys = [
                key
                for key in MANDATORY_ZIM_METADATA_KEYS
                if not self._metadata.get(key)
            ]
            raise ValueError(
                "Mandatory metadata are not all set. Missing metadata: "
                f'{",".join(missing_keys)}. You should prefer to use '
                "StandardMetadataList if possible to ensure this"
            )

        if (
            language := self._get_first_language_metadata_value()
        ) and not self.__indexing_configured:
            self.config_indexing(True, language)

        super().__enter__()

        for metadata in self._metadata.values():
            if isinstance(metadata, IllustrationMetadata):
                self.add_illustration(metadata.size, metadata.libzim_value)
            else:
                self.add_metadata(metadata)
        self._metadata.clear()

        return self

    def add_metadata(
        self,
        value: Metadata,
        mimetype: str = "text/plain;charset=UTF-8",
    ):
        """Really add the metadata to the ZIM, after ZIM creation has started.

        You would probably prefer to use config_metadata methods to check metadata
        before starting the ZIM, ensure all mandatory metadata are set, and avoid
        duplicate metadata name.
        """

        super().add_metadata(value.name, value.libzim_value, mimetype)

    def config_metadata(
        self,
        std_metadata: StandardMetadataList | list[Metadata],
        extra_metadata: list[Metadata] | None = None,
        *,
        fail_on_missing_prefix_in_extras: bool = True,
    ):
        """Checks and prepare list of ZIM metadata

        Checks ensure that metadata value can be converted to bytes, including all
        requirements of the ZIM specifications and optionally openZIM conventions.

        Metadata are only kept in memory at this stage, not yet passed to libzim.

        They will be passed to libzim / writen to the ZIM on creator.start().

        Arguments:
            std_metadata: standard metadata defined in the ZIM specifications.
                Prefer to use StandardMetadataList which ensure mandatory metadata are
                all set.
            extra_metadata: a list of extra metadata (not standard).
            fail_on_missing_prefix_in_extras: disable the default check which force the
                X- prefix on extra metadata name which is a convention to distinguish
                these extra metadata

        """
        for fail_on_missing_prefix, metadata in [
            (False, metadata)
            for metadata in (
                std_metadata.values()
                if isinstance(std_metadata, StandardMetadataList)
                else std_metadata
            )
        ] + [
            (fail_on_missing_prefix_in_extras, metadata)
            for metadata in extra_metadata or []
        ]:
            if fail_on_missing_prefix and not metadata.name.startswith("X-"):
                raise ValueError(
                    f"Metadata key {metadata.name} does not starts with X- as expected"
                )
            # if metadata.name in self._metadata:
            #     raise ValueError(f"{metadata.name} cannot be defined twice")
            self._metadata[metadata.name] = metadata

        return self

    def config_dev_metadata(
        self,
        extra_metadata: Metadata | list[Metadata] | None = None,
    ):
        """Calls minimal set of mandatory metadata with default values for dev

        Extra metadata can be passed, and they are not checked for proper key prefix
        """
        return self.config_metadata(
            std_metadata=DEFAULT_DEV_ZIM_METADATA,
            extra_metadata=(
                [extra_metadata]
                if isinstance(extra_metadata, Metadata)
                else extra_metadata
            ),
            fail_on_missing_prefix_in_extras=False,
        )

    def add_item_for(
        self,
        path: str,
        title: str | None = None,
        *,
        fpath: pathlib.Path | None = None,
        content: bytes | str | None = None,
        mimetype: str | None = None,
        is_front: bool | None = None,
        should_compress: bool | None = None,
        delete_fpath: bool | None = False,
        duplicate_ok: bool | None = None,
        callback: Callable | tuple[Callable, Any] | None = None,
        index_data: IndexData | None = None,
        auto_index: bool = True,
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

        if delete_fpath and fpath:
            cb = [delete_callback, fpath]
            if callback and callable(callback):
                cb.append(callback)
            elif callback:
                cb += list(callback)
            callback = tuple(cb)

        self.add_item(
            StaticItem(
                path=path,
                title=title,
                mimetype=mimetype,
                filepath=fpath,
                hints=hints,
                content=content,
                index_data=index_data,
                auto_index=auto_index,
            ),
            callback=callback,
            duplicate_ok=duplicate_ok,
        )
        return path

    def add_item(
        self,
        item: libzim.writer.Item,
        duplicate_ok: bool | None = None,
        callback: Callable | tuple[Callable, Any] | None = None,
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
        title: str | None = "",
        is_front: bool | None = None,
        duplicate_ok: bool | None = None,
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
                super().add_redirection(path, title or path, target_path, hints)
            except RuntimeError as exc:
                if not DUPLICATE_EXC_STR.match(str(exc)) or not duplicate_ok:
                    raise exc
        except Exception:
            if self.workaround_nocancel:
                self.can_finish = False  # pragma: no cover
            raise

    def finish(self, exc_type=None, exc_val=None, exc_tb=None):  # noqa: ARG002
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
