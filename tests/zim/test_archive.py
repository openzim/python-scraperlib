#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 nu

import pytest

from zimscraperlib.zim import Archive
from zimscraperlib.zim._libkiwix import convertTags


def test_metadata(small_zim_file):
    with Archive(small_zim_file) as zim:
        assert zim.metadata == {
            "Counter": "image/png=1;text/html=1",
            "Creator": "N/A",
            "Date": "2021-05-11",
            "Description": "N/A",
            "Language": "en",
            "Publisher": "N/A",
            "Scraper": "zimwriterfs-2.2.0",
            "Tags": "_ftindex:no",
            "Title": "Test ZIM file",
        }


def test_entry_by_id(small_zim_file):
    with Archive(small_zim_file) as zim:
        for id_ in range(zim.all_entry_count):
            assert zim.get_entry_by_id(id_)
        with pytest.raises(IndexError):
            zim.get_entry_by_id(zim.all_entry_count + 1)


def test_get_item(small_zim_file):
    with Archive(small_zim_file) as zim:
        assert zim.get_item("main.html").mimetype == "text/html"
        assert len(zim.get_content("main.html")) == 207


def test_suggestions(small_zim_file):
    with Archive(small_zim_file) as zim:
        assert zim.get_suggestions_count("test") == 1
        assert list(zim.get_suggestions("test")) == ["main.html"]


def test_suggestions_end_index(small_zim_file):
    with Archive(small_zim_file) as zim:
        assert zim.get_suggestions_count("test") == 1
        assert len(list(zim.get_suggestions("test", end=0))) == 0
        assert list(zim.get_suggestions("test", end=1)) == ["main.html"]


def test_search_no_fti(small_zim_file):
    with Archive(small_zim_file) as zim:
        with pytest.raises(
            RuntimeError, match="Cannot create Search without FT Xapian index"
        ):
            zim.get_search_results_count("test")
        with pytest.raises(
            RuntimeError, match="Cannot create Search without FT Xapian index"
        ):
            zim.get_search_results("test")


@pytest.mark.slow
def test_search(real_zim_file):
    with Archive(real_zim_file) as zim:
        assert zim.get_search_results_count("test") > 0
        assert "A/Diesel_emissions_scandal" in list(zim.get_search_results("test"))


@pytest.mark.slow
def test_search_end_index(real_zim_file):
    with Archive(real_zim_file) as zim:
        assert list(zim.get_search_results("test", end=0)) == []
        assert "A/Diesel_emissions_scandal" in list(
            zim.get_search_results("test", end=1)
        )


def test_counters(small_zim_file):
    with Archive(small_zim_file) as zim:
        assert zim.counters == {"image/png": 1, "text/html": 1}


def test_get_tags(small_zim_file, real_zim_file):
    with Archive(small_zim_file) as zim:
        assert zim.get_tags() == ["_ftindex:no"]
        assert zim.get_tags(libkiwix=True) == [
            "_ftindex:no",
            "_pictures:yes",
            "_videos:yes",
            "_details:yes",
        ]
        assert zim.tags == zim.get_tags()

    with Archive(real_zim_file) as zim:
        assert zim.get_tags() == [
            "wikipedia",
            "_category:wikipedia",
            "_pictures:no",
            "_videos:no",
            "_details:yes",
            "_ftindex:yes",
        ]
        assert zim.get_tags(libkiwix=True) == [
            "wikipedia",
            "_category:wikipedia",
            "_pictures:no",
            "_videos:no",
            "_details:yes",
            "_ftindex:yes",
        ]
        assert zim.tags == zim.get_tags()


def test_libkiwix_convert_tags():
    assert convertTags("") == [
        "_ftindex:no",
        "_pictures:yes",
        "_videos:yes",
        "_details:yes",
    ]
    assert convertTags("nopic") == [
        "_pictures:no",
        "_ftindex:no",
        "_videos:yes",
        "_details:yes",
    ]
    assert convertTags("novid") == [
        "_videos:no",
        "_ftindex:no",
        "_pictures:yes",
        "_details:yes",
    ]
    assert convertTags("nodet") == [
        "_details:no",
        "_ftindex:no",
        "_pictures:yes",
        "_videos:yes",
    ]
    assert convertTags("_ftindex") == [
        "_ftindex:yes",
        "_pictures:yes",
        "_videos:yes",
        "_details:yes",
    ]
