#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 nu

""" ZIM Archive helper

    Convenient subclass of libzim.reader.Archive with:
    - direct access to Item from path
    - direct access to suggestions and suggestions count
    - direct access to search results and number of results
    - public Entry access by Id"""

from __future__ import annotations

from collections.abc import Iterable

import libzim.reader  # pyright: ignore
import libzim.search  # Query, Searcher  # pyright: ignore
import libzim.suggestion  # SuggestionSearcher  # pyright: ignore

from zimscraperlib.zim._libkiwix import convertTags, parseMimetypeCounter
from zimscraperlib.zim.items import Item


class Archive(libzim.reader.Archive):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    @property
    def metadata(self) -> dict[str, str]:
        """key: value for all non-illustration metadata listed in .metadata_keys"""
        return {
            key: self.get_text_metadata(key)
            for key in self.metadata_keys
            if not key.startswith("Illustration_")
        }

    @property
    def tags(self):
        return self.get_tags()

    def get_tags(self, libkiwix: bool = False) -> list[str]:  # noqa: FBT001, FBT002
        """List of ZIM tags, optionnaly expanded with libkiwix's hints"""
        try:
            tags_meta = self.get_text_metadata("Tags")
        except RuntimeError:  # pragma: no cover
            tags_meta = ""

        if libkiwix:
            return convertTags(tags_meta)

        return tags_meta.split(";")

    def get_text_metadata(self, name: str) -> str:
        """Decoded value of a text metadata"""
        return super().get_metadata(name).decode("UTF-8")

    def get_entry_by_id(self, id_: int) -> libzim.reader.Entry:
        """Entry from its Id in ZIM"""
        return self._get_entry_by_id(id_)

    def get_item(self, path: str) -> Item:
        """Item from a path"""
        return self.get_entry_by_path(path).get_item()

    def get_content(self, path: str) -> bytes:
        """Actual content from a path"""
        return bytes(self.get_item(path).content)

    def get_suggestions(
        self, query: str, start: int = 0, end: int | None = None
    ) -> Iterable[str]:
        """paths iterator over suggestion matches for query"""
        suggestion = libzim.suggestion.SuggestionSearcher(self).suggest(query)
        if end is None:
            end = suggestion.getEstimatedMatches()
        return suggestion.getResults(start, end)

    def get_suggestions_count(self, query: str) -> int:
        """Estimated number of suggestion matches for query"""
        suggestion = libzim.suggestion.SuggestionSearcher(self).suggest(query)
        return suggestion.getEstimatedMatches()

    def get_search_results(
        self, query: str, start: int = 0, end: int | None = None
    ) -> Iterable[str]:
        """paths iterator over search results for query"""
        search = libzim.search.Searcher(self).search(
            libzim.search.Query().set_query(query)
        )
        if end is None:
            end = search.getEstimatedMatches()
        return search.getResults(start, end)

    def get_search_results_count(self, query: str) -> int:
        """Estimated number of search results for query"""
        search = libzim.search.Searcher(self).search(
            libzim.search.Query().set_query(query)
        )
        return search.getEstimatedMatches()

    @property
    def counters(self) -> dict[str, int]:
        try:
            return parseMimetypeCounter(self.get_text_metadata("Counter"))
        except RuntimeError:  # pragma: no cover (no ZIM avail to test itl)
            return {}  # pragma: no cover
