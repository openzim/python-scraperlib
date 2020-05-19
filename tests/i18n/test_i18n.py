#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import locale
import pathlib

import pytest

from zimscraperlib.i18n import setlocale, get_language_details, _


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
                "english": "Chinese",
                "iso_types": ["part1"],
                "querytype": "locale",
                "query": "zh-Hans",
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
                "english": "Hindi",
                "iso_types": ["part2b", "part2t", "part3"],
                "querytype": "purecode",
                "query": "hin",
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
                "english": "Japanese",
                "iso_types": ["name"],
                "querytype": "languagename",
                "query": "Japanese",
            },
        ),
        (
            "afa",
            {
                "iso-639-1": "",
                "iso-639-2b": "afa",
                "iso-639-2t": "afa",
                "iso-639-3": "",
                "iso-639-5": "afa",
                "english": "Afro-Asiatic languages",
                "iso_types": ["part2b", "part2t", "part5"],
                "querytype": "purecode",
                "query": "afa",
            },
        ),
        (
            "afro-asiatic languages",
            {
                "iso-639-1": "",
                "iso-639-2b": "afa",
                "iso-639-2t": "afa",
                "iso-639-3": "",
                "iso-639-5": "afa",
                "english": "Afro-Asiatic languages",
                "iso_types": ["name"],
                "querytype": "languagename",
                "query": "afro-asiatic languages",
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
                "english": "Mandarin Chinese",
                "iso_types": ["part3"],
                "querytype": "purecode",
                "query": "cmn",
            },
        ),
        ("fake-lang", None,),
        ("fake", None,),
        ("C#", None,),
        ("fks", None,),
    ],
)
def test_lang_details(query, expected):
    assert get_language_details(query) == expected


@pytest.mark.parametrize(
    "lang,expected",
    [("en", "Hello World!"), ("fr", "Bonjour monde !"), ("pt_BR.utf8", "Olá Mundo!")],
)
def test_translation(lang, expected):
    setlocale(pathlib.Path(__file__).parent, lang)
    assert _("Hello World!") == expected
