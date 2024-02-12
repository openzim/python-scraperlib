#!/usr/bin/env python3
# vim: ai ts=4 sts=4 et sw=4 nu

import locale
import pathlib

import pytest

from zimscraperlib.i18n import (
    NotFound,
    _,
    find_language_names,
    get_language_details,
    setlocale,
)


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
    "query,expected",
    [
        (
            "zh-Hans",
            {
                "iso-639-1": "zh",
                "iso-639-2b": "chi",
                "iso-639-2t": "zho",
                "iso-639-3": "zho",
                "iso-639-5": "",
                "english": "Chinese (Simplified)",
                "iso_types": ["part1"],
                "querytype": "locale",
                "query": "zh-Hans",
                "native": "中文 (简体)",
            },
        ),
        (
            "hi",
            {
                "iso-639-1": "hi",
                "iso-639-2b": "hin",
                "iso-639-2t": "hin",
                "iso-639-3": "hin",
                "iso-639-5": "",
                "english": "Hindi",
                "iso_types": ["part1"],
                "querytype": "purecode",
                "query": "hi",
                "native": "हिन्दी",
            },
        ),
        (
            "hin",
            {
                "iso-639-1": "hi",
                "iso-639-2b": "hin",
                "iso-639-2t": "hin",
                "iso-639-3": "hin",
                "iso-639-5": "",
                "english": "Hindi (India)",
                "iso_types": ["part2b", "part2t", "part3"],
                "querytype": "purecode",
                "query": "hin",
                "native": "हिन्दी (भारत)",
            },
        ),
        (
            "Japanese",
            {
                "iso-639-1": "ja",
                "iso-639-2b": "jpn",
                "iso-639-2t": "jpn",
                "iso-639-3": "jpn",
                "iso-639-5": "",
                "english": "Japanese (Japan)",
                "iso_types": ["name"],
                "querytype": "languagename",
                "query": "Japanese",
                "native": "日本語 (日本)",
            },
        ),
        (
            "afa",
            {
                "iso-639-1": "",
                "iso-639-2b": "afa",
                "iso-639-2t": "",
                "iso-639-3": "",
                "iso-639-5": "afa",
                "english": "Afro-Asiatic languages",
                "iso_types": ["part2b", "part5"],
                "querytype": "purecode",
                "query": "afa",
                "native": "Afro-Asiatic languages",
            },
        ),
        (
            "afro-asiatic languages",
            {
                "iso-639-1": "",
                "iso-639-2b": "afa",
                "iso-639-2t": "",
                "iso-639-3": "",
                "iso-639-5": "afa",
                "english": "Afro-Asiatic languages",
                "iso_types": ["name"],
                "querytype": "languagename",
                "query": "afro-asiatic languages",
                "native": "Afro-Asiatic languages",
            },
        ),
        (
            "cmn",
            {
                "iso-639-1": "zh",
                "iso-639-2b": "chi",
                "iso-639-2t": "zho",
                "iso-639-3": "cmn",
                "iso-639-5": "",
                "english": "Chinese (Simplified, China)",
                "iso_types": ["part3"],
                "querytype": "purecode",
                "query": "cmn",
                "native": "中文 (简体, 中国)",
            },
        ),
        (
            "fake-lang",
            None,
        ),
        (
            "fake",
            None,
        ),
        (
            "C#",
            None,
        ),
        (
            "fks",
            None,
        ),
        (
            "arq",
            {
                "iso-639-1": "ar",
                "iso-639-2b": "ara",
                "iso-639-2t": "ara",
                "iso-639-3": "arq",
                "iso-639-5": "",
                "english": "Arabic (Egypt)",
                "iso_types": ["part3"],
                "native": "العربية (مصر)",
                "querytype": "purecode",
                "query": "arq",
            },
        ),
        (
            "ar-ma",
            {
                "iso-639-1": "ar",
                "iso-639-2b": "ara",
                "iso-639-2t": "ara",
                "iso-639-3": "ara",
                "iso-639-5": "",
                "english": "Arabic (Morocco)",
                "iso_types": ["part1"],
                "native": "العربية (المغرب)",
                "querytype": "locale",
                "query": "ar-ma",
            },
        ),
    ],
)
def test_lang_details(query, expected):
    if expected is None:
        assert get_language_details(query, failsafe=True) == expected
        with pytest.raises(NotFound):
            get_language_details(query)
    else:
        assert get_language_details(query) == expected


@pytest.mark.parametrize(
    "query,expected",
    [
        ("fr", ("français", "French")),
        ("en", ("English", "English")),
        ("bm", ("bamanakan", "Bambara")),
        ("zh", ("中文", "Chinese")),
        ("ar", ("العربية", "Arabic")),
    ],
)
def test_lang_name(query, expected):
    assert find_language_names(query) == expected


@pytest.mark.parametrize(
    "lang,expected",
    [("en", "Hello World!"), ("fr", "Bonjour monde !"), ("pt_BR.utf8", "Olá Mundo!")],
)
def test_translation(lang, expected):
    setlocale(pathlib.Path(__file__).parent, lang)
    assert _("Hello World!") == expected
