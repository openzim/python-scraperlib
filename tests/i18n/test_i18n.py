from typing import Any
from unittest.mock import Mock

import pytest

from zimscraperlib.i18n import (
    Language,
    NotFoundError,
    find_language_names,
    get_language,
    get_language_or_none,
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
                "iso-639-5": None,
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
                "iso-639-5": None,
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
                "iso-639-5": None,
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
                "iso-639-5": None,
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
                "iso-639-1": None,
                "iso-639-2b": "afa",
                "iso-639-2t": "afa",
                "iso-639-3": None,
                "iso-639-5": "afa",
                "english": "Afro-Asiatic languages",
                "iso_types": ["part2b", "part2t", "part5"],
                "querytype": "purecode",
                "query": "afa",
                "native": "Afro-Asiatic languages",
            },
        ),
        (
            "afro-asiatic languages",
            {
                "iso-639-1": None,
                "iso-639-2b": "afa",
                "iso-639-2t": "afa",
                "iso-639-3": None,
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
                "iso-639-5": None,
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
                "iso-639-5": None,
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
                "iso-639-5": None,
                "english": "Arabic (Morocco)",
                "iso_types": ["part1"],
                "native": "العربية (المغرب)",
                "querytype": "locale",
                "query": "ar-ma",
            },
        ),
    ],
)
def test_lang_details(query: str, expected: dict[str, Any] | None):
    if expected is None:
        assert get_language_or_none(query) == expected
        with pytest.raises(NotFoundError):
            get_language(query)
    else:
        result = get_language_or_none(query)
        assert result
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
def test_lang_name(query: str, expected: tuple[str, str]):
    assert find_language_names(query) == expected


@pytest.mark.parametrize(
    "babel_native_return, babel_english_return, expected_native, expected_english",
    [
        ("Native value", "English value", "Native value", "English value"),
        (None, "English value", "German", "German"),
        ("Native value", None, "German", "German"),
    ],
)
def test_find_language_names(
    mocker: Mock,
    babel_native_return: str | None,
    babel_english_return: str | None,
    expected_native: str,
    expected_english: str,
):
    mock_locale = Mock()

    def mock_display_name(lang: str | None = None) -> str | None:
        return babel_native_return if lang is None else babel_english_return

    mock_locale.get_display_name.side_effect = mock_display_name

    mocker.patch("babel.Locale.parse", return_value=mock_locale)

    assert find_language_names("de") == (expected_native, expected_english)


@pytest.mark.parametrize(
    "query_left, query_right",
    [
        pytest.param("ara", "Arabic", id="arabic"),
        pytest.param("fra", "French", id="french"),
    ],
)
def test_lang_details_equality(query_left: str, query_right: str):
    assert Language(query_left) == Language(query_right)


@pytest.mark.parametrize(
    "patch_attribute",
    [
        "iso_639_1",
        "iso_639_2b",
        "iso_639_2t",
        "iso_639_3",
        "iso_639_5",
        "english",
        "native",
    ],
)
def test_lang_details_inequality_with_patch(patch_attribute: str):
    lang_and_details_patched = get_language("arq")
    setattr(lang_and_details_patched, patch_attribute, "foo")
    assert get_language("arq") != lang_and_details_patched


@pytest.mark.parametrize(
    "query_left, query_right",
    [
        pytest.param("fra", "ara", id="different_lang"),
        pytest.param("ar", "ar-AE", id="different_locale"),
    ],
)
def test_lang_details_inequality(query_left: str, query_right: str):
    assert get_language(query_left) != get_language(query_right)


def test_lang_details_inequality_objects():
    assert get_language("ara") != "ara"


@pytest.mark.parametrize(
    "query,expected",
    [
        (
            "fra",
            {
                "english": "French (France)",
                "iso-639-1": "fr",
                "iso-639-2b": "fre",
                "iso-639-2t": "fra",
                "iso-639-3": "fra",
                "iso-639-5": None,
                "iso-types": [
                    "part2t",
                    "part3",
                ],
                "native": "français (France)",
                "query": "fra",
                "querytype": "purecode",
            },
        ),
        (
            "zh",
            {
                "english": "Chinese",
                "iso-639-1": "zh",
                "iso-639-2b": "chi",
                "iso-639-2t": "zho",
                "iso-639-3": "zho",
                "iso-639-5": None,
                "iso-types": [
                    "part1",
                ],
                "native": "中文",
                "query": "zh",
                "querytype": "purecode",
            },
        ),
        (
            "ar",
            {
                "english": "Arabic",
                "iso-639-1": "ar",
                "iso-639-2b": "ara",
                "iso-639-2t": "ara",
                "iso-639-3": "ara",
                "iso-639-5": None,
                "iso-types": [
                    "part1",
                ],
                "native": "العربية",
                "query": "ar",
                "querytype": "purecode",
            },
        ),
    ],
)
def test_lang_to_dict(query: str, expected: dict[str, str | None | list[str]]):
    assert Language(query).todict() == expected


@pytest.mark.parametrize(
    "query,expected",
    [
        (
            "fra",
            'Language(iso_639_1="fr", iso_639_2b="fre", iso_639_2t="fra", '
            'iso_639_3="fra", iso_639_5="None", english="French (France)", '
            "iso_types=\"['part2t', 'part3']\", native=\"français (France)\", "
            'querytype="purecode", query="fra")',
        ),
        (
            "zh",
            'Language(iso_639_1="zh", iso_639_2b="chi", iso_639_2t="zho", '
            'iso_639_3="zho", iso_639_5="None", english="Chinese", '
            'iso_types="[\'part1\']", native="中文", querytype="purecode", query="zh")',
        ),
        (
            "ar",
            'Language(iso_639_1="ar", iso_639_2b="ara", iso_639_2t="ara", '
            'iso_639_3="ara", iso_639_5="None", english="Arabic", '
            'iso_types="[\'part1\']", native="العربية", querytype="purecode", '
            'query="ar")',
        ),
    ],
)
def test_lang_repr(query: str, expected: str):
    assert Language(query).__repr__() == expected


@pytest.mark.parametrize(
    "query,expected",
    [
        ("fra", "fra: French (France)"),
        ("zh", "zho: Chinese"),
        ("ar", "ara: Arabic"),
    ],
)
def test_lang_str(query: str, expected: str):
    assert f"{Language(query)}" == expected
