#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

""" ZIM Archive helper

    Convenient subclass of libzim.reader.Archive with:
    - direct access to Item from path
    - direct access to suggestions and suggestions count
    - direct access to search results and number of results
    - public Entry access by Id"""

from typing import Dict, Iterable, List, Optional

import libzim.reader
import libzim.search  # Query, Searcher
import libzim.suggestion  # SuggestionSearcher

from ._libkiwix import convertTags, getArticleCount, getMediaCount, parseMimetypeCounter
from .items import Item


class Archive(libzim.reader.Archive):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    @property
    def metadata(self) -> Dict[str, str]:
        """key: value for all non-illustration metadata listed in .metadata_keys"""
        return {
            key: self.get_text_metadata(key)
            for key in self.metadata_keys
            if not key.startswith("Illustration_")
        }

    @property
    def tags(self):
        return self.get_tags()

    def get_tags(self, libkiwix: bool = False) -> List[str]:
        """List of ZIM tags, optionnaly expanded with libkiwix's hints"""
        try:
            tags_meta = self.get_text_metadata("Tags")
        except RuntimeError:  # pragma: nocover
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
        self, query: str, start: int = 0, end: Optional[int] = None
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
        self, query: str, start: int = 0, end: Optional[int] = None
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
    def counters(self) -> Dict[str, int]:
        try:
            return parseMimetypeCounter(self.get_text_metadata("Counter"))
        except RuntimeError:  # pragma: no cover (no ZIM avail to test itl)
            return {}  # pragma: no cover

    @property
    def article_counter(self) -> int:
        """Nb of *articles* in the ZIM, using counters (from libkiwix)"""

        # [libkiwix HACK]
        # getArticleCount() returns different things depending on
        # the "version" of the zim.
        # On old zim (<=6), it returns the number of entry in `A` namespace
        # On recent zim (>=7), it returns:
        #  - the number of entry in `C` namespace (==getEntryCount)
        #    if no frontArticleIndex is present
        #  - the number of front article if a frontArticleIndex is present
        # The use case >=7 without frontArticleIndex is pretty rare so we don't care
        # We can detect if we are reading a zim <= 6
        # by checking if we have a newNamespaceScheme.
        if self.has_new_namespace_scheme:
            return self.article_count
        return getArticleCount(self.counters)

    @property
    def media_counter(self) -> int:
        """Nb of *medias* in the ZIM, using counters (from libkiwix)"""
        return getMediaCount(self.counters)
