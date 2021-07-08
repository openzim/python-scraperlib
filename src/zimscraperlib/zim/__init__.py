#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

""" Zim file creation tools

    zim.creator: create files by manually adding each article
    zim.filesystem: zimwriterfs-like creation from a build folder
    zim.providers: contentProvider for serving libzim with data
    zim.items: item to add to creator"""

from libzim.writer import Blob
from libzim.reader import Archive as _Archive

from .creator import Creator
from .filesystem import make_zim_file
from .items import Item, StaticItem, URLItem
from .providers import FileProvider, StringProvider, FileLikeProvider, URLProvider

__all__ = [
    "Archive",
    "Creator",
    "make_zim_file",
    "Item",
    "StaticItem",
    "URLItem",
    "FileProvider",
    "StringProvider",
    "FileLikeProvider",
    "URLProvider",
    "Blob",
]


class Archive(_Archive):
    def get_item(self, path) -> Item:
        """Item from a path"""
        return self.get_entry_by_path(path).get_item()
