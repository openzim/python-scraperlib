import pathlib
import re
from typing import Any

import pytest

from zimscraperlib.zim import Archive, Creator
from zimscraperlib.zim.dedup import Deduplicator


def test_deduplicator(
    tmp_path: pathlib.Path,
    png_image: pathlib.Path,
    html_file: pathlib.Path,
    html_str: str,
    html_str_cn: str,
):
    main_path = "welcome"

    png_data = png_image.read_bytes()

    def add_items(creator_or_deduplicator: Any):
        creator_or_deduplicator.add_item_for(
            "welcome1", "wel1", content=html_str, is_front=True
        )
        creator_or_deduplicator.add_item_for(
            "welcome2", "wel2", content=html_str, is_front=True
        )
        creator_or_deduplicator.add_item_for(
            "dedup/welcome3", "wel3", content=html_str, is_front=True
        )
        creator_or_deduplicator.add_item_for(
            "dedup/welcome4", "wel4", content=html_str, is_front=True
        )
        creator_or_deduplicator.add_item_for(
            "prefix/dedup/welcome5", "wel5", content=html_str, is_front=True
        )
        creator_or_deduplicator.add_item_for("image1", None, fpath=png_image)
        creator_or_deduplicator.add_item_for("image2", None, content=png_data)
        creator_or_deduplicator.add_item_for("dedup/image3", None, fpath=png_image)
        creator_or_deduplicator.add_item_for("dedup/image4", None, content=png_data)
        creator_or_deduplicator.add_item_for("dedup/html", None, fpath=html_file)
        creator_or_deduplicator.add_item_for("dedup/html_cn", None, content=html_str_cn)
        creator_or_deduplicator.add_item_for(
            "prefix/dedup/image5", None, content=png_data
        )

    fpath_without_dedup = tmp_path / "zim_without_dedup.zim"
    with Creator(fpath_without_dedup, main_path).config_dev_metadata() as creator:
        add_items(creator)

    assert fpath_without_dedup.exists()

    fpath_with_dedup = tmp_path / "zim_with_dedup.zim"
    with Creator(fpath_with_dedup, main_path).config_dev_metadata() as creator:
        deduplicator = Deduplicator(creator)
        deduplicator.filters.append(re.compile("^foo/.*$"))
        deduplicator.filters.append(re.compile("^dedup/.*$"))
        deduplicator.filters.append(re.compile("^bar/.*$"))
        add_items(deduplicator)

        # added_items contains only original items, not the duplicates
        assert set(deduplicator.added_items.values()) == {
            "dedup/welcome3",
            "dedup/image3",
            "dedup/html_cn",
        }

    assert fpath_with_dedup.exists()

    # check that deduplication has a consequence on ZIM size
    assert (
        fpath_without_dedup.lstat().st_size - fpath_with_dedup.lstat().st_size
    ) > 3000  # 3291 as of libzim 9.3

    for zim_path in [fpath_with_dedup, fpath_without_dedup]:
        reader = Archive(zim_path)

        assert reader.all_entry_count == 24

        for html_path in [
            "welcome1",
            "welcome2",
            "dedup/welcome3",
            "dedup/welcome4",
            "prefix/dedup/welcome5",
            "dedup/html",
        ]:
            assert bytes(reader.get_item(html_path).content).decode() == html_str
        assert bytes(reader.get_item("dedup/html_cn").content).decode() == html_str_cn

        for img_path in [
            "image1",
            "image2",
            "dedup/image3",
            "dedup/image4",
            "prefix/dedup/image5",
        ]:
            assert bytes(reader.get_item(img_path).content) == png_data


def test_missing_content(tmp_path: pathlib.Path):
    with Creator(tmp_path / "test.zin", "foo").config_dev_metadata() as creator:
        deduplicator = Deduplicator(creator)
        deduplicator.filters.append(re.compile(".*"))
        with pytest.raises(Exception, match="Either content or fpath are mandatory"):
            deduplicator.add_item_for("welcome", None)
