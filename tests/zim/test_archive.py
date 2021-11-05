#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import pytest

from zimscraperlib.zim import Archive


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
        assert "main.html" in list(zim.get_suggestions("test"))


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


def test_search(real_zim_file):
    with Archive(real_zim_file) as zim:
        assert zim.get_search_results_count("test") > 0
        assert "A/Diesel_emissions_scandal" in list(zim.get_search_results("test"))


def test_counters(small_zim_file):
    with Archive(small_zim_file) as zim:
        assert zim.counters == {"image/png": 1, "text/html": 1}


def test_article_counter(small_zim_file):
    with Archive(small_zim_file) as zim:
        assert zim.article_counter == 1


def test_media_counter(small_zim_file):
    with Archive(small_zim_file) as zim:
        assert zim.media_counter == 1
