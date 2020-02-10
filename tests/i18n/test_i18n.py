#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import locale

import pytest

from zimscraperlib.i18n import setlocale, get_language_details


@pytest.mark.parametrize(
    "code,expected",
    [("en", "en_US.UTF-8"), ("en_us", "en_US.UTF-8"), ("en.utf8", "en_US.UTF-8")],
)
def test_setlocale(tmp_path, code, expected):
    assert setlocale(tmp_path, code) == expected


def test_selocale_unsupported(tmp_path):
    with pytest.raises(locale.Error):
        setlocale(tmp_path, "bam")


@pytest.mark.parametrize(
    "iso_639_3,expected",
    [
        (
            "zh-Hans",
            {
                "code": "zh-Hans",
                "iso-639-1": "zh",
                "english": "Simplified Chinese",
                "native": "简化字",
            },
        ),
        (
            "zh-Hant",
            {
                "code": "zh-Hant",
                "iso-639-1": "zh",
                "english": "Traditional Chinese",
                "native": "正體字",
            },
        ),
        (
            "iw",
            {"code": "iw", "iso-639-1": "he", "english": "Hebrew", "native": "עברית"},
        ),
        (
            "es-419",
            {
                "code": "es-419",
                "iso-639-1": "es-419",
                "english": "Spanish",
                "native": "Español",
            },
        ),
        (
            "multi",
            {
                "code": "mul",
                "iso-639-1": "en",
                "english": "Multiple Languages",
                "native": "Multiple Languages",
            },
        ),
        (
            "fra",
            {
                "code": "fra",
                "english": "French",
                "iso-639-1": "fr",
                "native": "français; langue française",
            },
        ),
        (
            "bam",
            {
                "code": "bam",
                "english": "Bambara",
                "iso-639-1": "bm",
                "native": "bamanankan",
            },
        ),
        (
            "ara",
            {
                "code": "ara",
                "english": "Arabic",
                "iso-639-1": "ar",
                "native": "العربية",
            },
        ),
        (
            "fake",
            {"code": "fake", "english": "fake", "iso-639-1": "fake", "native": "fake"},
        ),
    ],
)
def test_lang_details(iso_639_3, expected):
    assert get_language_details(iso_639_3) == expected
