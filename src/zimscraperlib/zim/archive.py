#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

""" ZIM Archive helper

    Convenient subclass of libzim.reader.Archive with:
    - direct access to Item from path
    - direct access to suggestions and suggestions count
    - direct access to search results and number of results
    - public Entry access by Id"""

from typing import Dict, Iterable, Optional

import libzim.reader
import libzim.search  # Query, Searcher
import libzim.suggestion  # SuggestionSearcher

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
            key: self.get_metadata(key).decode("UTF-8")
            for key in self.metadata_keys
            if not key.startswith("Illustration_")
        }

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
