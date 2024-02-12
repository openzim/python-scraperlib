#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 nu

""" ZIM file creation tools

    zim.creator: create files by manually adding each article
    zim.filesystem: zimwriterfs-like creation from a build folder
    zim.providers: contentProvider for serving libzim with data
    zim.items: item to add to creator
    zim.archive: read ZIM files, accessing or searching its content"""

from libzim.writer import Blob  # pyright: ignore

from zimscraperlib.zim.archive import Archive
from zimscraperlib.zim.creator import Creator
from zimscraperlib.zim.filesystem import make_zim_file
from zimscraperlib.zim.items import Item, StaticItem, URLItem
from zimscraperlib.zim.providers import (
    FileLikeProvider,
    FileProvider,
    StringProvider,
    URLProvider,
)

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
