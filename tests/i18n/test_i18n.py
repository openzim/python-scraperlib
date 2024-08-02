#!/usr/bin/env python3
# vim: ai ts=4 sts=4 et sw=4 nu

from unittest.mock import Mock

import pytest

from zimscraperlib.i18n import (
    Lang,
    NotFoundError,
    find_language_names,
    get_language_details,
)


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
        with pytest.raises(NotFoundError):
            get_language_details(query)
    else:
        result = get_language_details(query)
        assert result == expected
        if result:
            assert result.iso_639_1 == expected.get("iso-639-1")
            assert result.iso_639_2b == expected.get("iso-639-2b")
            assert result.iso_639_2t == expected.get("iso-639-2t")
            assert result.iso_639_3 == expected.get("iso-639-3")
            assert result.iso_639_5 == expected.get("iso-639-5")
            assert result.english == expected.get("english")
            assert result.native == expected.get("native")
            assert result.iso_types == expected.get("iso_types")
            assert result.query == expected.get("query")
            assert result.querytype == expected.get("querytype")


@pytest.mark.parametrize(
    "query,expected",
    [
        ("fr", ("français", "French")),
        ("en", ("English", "English")),
        ("bm", ("bamanakan", "Bambara")),
        ("zh", ("中文", "Chinese")),
        ("ar", ("العربية", "Arabic")),
        ("qq", ("qq", "qq")),
    ],
)
def test_lang_name(query, expected):
    assert find_language_names(query) == expected


@pytest.mark.parametrize(
    "dict_data",
    [{}, {"iso-639-1": "ar"}],
)
def test_lang_equals(dict_data):
    assert Lang(dict_data) == Lang(dict_data)
    assert Lang(dict_data) == Lang({**dict_data})


@pytest.mark.parametrize(
    "dict_data_left, dict_data_right",
    [
        ({}, {"iso-639-1": "ar"}),
        ({"iso-639-1": "ar"}, {"iso-639-1": "ab"}),
        ({"iso-639-1": "ar"}, {"iso-639-2": "ar"}),
    ],
)
def test_lang_not_equals(dict_data_left, dict_data_right):
    assert Lang(dict_data_left) != Lang(dict_data_right)
    assert Lang(dict_data_left) != "foo"


@pytest.mark.parametrize(
    "babel_native_return, babel_english_return, expected_native, expected_english",
    [
        ("Native value", "English value", "Native value", "English value"),
        (None, "English value", "German", "German"),
        ("Native value", None, "German", "German"),
    ],
)
def test_find_language_names(
    mocker, babel_native_return, babel_english_return, expected_native, expected_english
):
    mock_locale = Mock()
    mock_locale.get_display_name.side_effect = lambda lang=None: (
        babel_native_return if lang is None else babel_english_return
    )

    mocker.patch("babel.Locale.parse", return_value=mock_locale)

    assert find_language_names("de") == (expected_native, expected_english)
