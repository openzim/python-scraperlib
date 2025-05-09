import pathlib
import re
from typing import Any

import xxhash
from libzim.writer import Hint  # pyright: ignore[reportMissingModuleSource]

from zimscraperlib.zim.creator import Creator

CONTENT_BUFFER_READ_SIZE = 1048576  # 1M


class Deduplicator:
    """Automatically deduplicate potential ZIM items before adding them to the ZIM

    This class automatically computes the digest of every item added to the ZIM, and
    either add the entry (if item is not yet inside the ZIM) or an alias (if item with
    same digest has already been added inside the ZIM).

    This class must be configured with filters to specifiy which items paths to
    consider. It is of course possible to consider all paths (i.e. all items) with a
    wide regex or to operate on a subset (e.g. all images) with more precise filters.
    Item is considered for deduplication if any filter matches. It is recommended to
    properly configure these filters to save time / memory by automatically ignoring
    items which are known to always be different and / or be too numerous.

    Only the digest and path of items matching the filters are computed and stored.

    The xxh32 algorithm (https://github.com/Cyan4973/xxHash) which is known to be good
    at avoiding collision with minimal memory and CPU footprint is used, so the sheer
    memory consumption will come from the paths we have to keep. This hashing algorithm
    is not meant for security purpose since one might infer original content from
    hashes, but this is not our use case.
    """

    def __init__(self, creator: Creator):
        self.creator = creator
        self.filters: list[re.Pattern[str]] = []
        self.added_items: dict[bytes, str] = {}

    def add_item_for(
        self,
        path: str,
        title: str | None = None,
        *,
        fpath: pathlib.Path | None = None,
        content: bytes | str | None = None,
        **kwargs: Any,
    ):
        """Add an item at given path or an alias"""
        existing_item = None
        if any(_filter.match(path) is not None for _filter in self.filters):
            if content:
                digest = xxhash.xxh32(
                    content.encode() if isinstance(content, str) else content
                ).digest()
            else:
                if not fpath:
                    raise Exception("Either content or fpath are mandatory")
                xxh32 = xxhash.xxh32()
                with open(fpath, "rb") as f:
                    while True:
                        data = f.read(CONTENT_BUFFER_READ_SIZE)  # read content in chunk
                        if not data:
                            break
                        xxh32.update(data)
                digest = xxh32.digest()

            if existing_item := self.added_items.get(digest):
                self.creator.add_alias(
                    path,
                    targetPath=existing_item,
                    title=title or path,
                    hints={Hint.FRONT_ARTICLE: True} if kwargs.get("is_front") else {},
                )
                return
            else:
                self.added_items[digest] = path

        self.creator.add_item_for(path, title, fpath=fpath, content=content, **kwargs)
