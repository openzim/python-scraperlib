#!/usr/bin/env python3
# vim: ai ts=4 sts=4 et sw=4 nu

from __future__ import annotations

import re

import babel
import iso639
import iso639.exceptions

ISO_LEVELS = ["1", "2b", "2t", "3", "5"]


class NotFoundError(ValueError):
    pass


class Lang(dict):

    @property
    def iso_639_1(self) -> str | None:
        """ISO-639-1 language code"""
        return self["iso-639-1"]

    @property
    def iso_639_2b(self) -> str | None:
        """ISO-639-2b language code"""
        return self["iso-639-2b"]

    @property
    def iso_639_2t(self) -> str | None:
        """ISO-639-2t language code"""
        return self["iso-639-2t"]

    @property
    def iso_639_3(self) -> str | None:
        """ISO-639-3 language code"""
        return self["iso-639-3"]

    @property
    def iso_639_5(self) -> str | None:
        """ISO-639-5 language code"""
        return self["iso-639-5"]

    @property
    def english(self) -> str:
        """language name in English"""
        return self["english"]

    @property
    def native(self) -> str:
        """language name in native language"""
        return self["native"]

    @property
    def iso_types(self) -> list[str]:
        """list of supported iso types"""
        return self["iso_types"]

    @property
    def query(self) -> list[str]:
        """Query issued for these language details"""
        return self["query"]

    @property
    def querytype(self) -> list[str]:
        """Type of query issued to retrieve language details"""
        return self["querytype"]


def get_iso_lang_data(lang: str) -> tuple[Lang, Lang | None]:
    """ISO-639-x languages details for lang. Raises NotFoundError

    Returns a tuple (main_language, macro_language | None)"""

    iso_types = []

    try:
        isolang = iso639.Lang(lang)
    except (
        iso639.exceptions.InvalidLanguageValue,
        iso639.exceptions.DeprecatedLanguageValue,
    ) as exc:
        raise NotFoundError("Not a valid iso language name/code") from exc

    def replace_types(new_type: str) -> str:
        # convert new iso_types from iso639-lang Pypi package to old iso_types from
        # iso-639 package, since we were returning these values for a long time
        if new_type == "pt1":
            return "part1"
        elif new_type == "pt2b":
            return "part2b"
        elif new_type == "pt2t":
            return "part2t"
        elif new_type == "pt3":
            return "part3"
        elif new_type == "pt5":
            return "part5"
        return new_type

    for code_type in [f"pt{lang_}" for lang_ in ISO_LEVELS] + ["name"]:
        # the `if` condition below is a bit hackish but it is the only way to know
        # if the passed value is matching a code type or not with new python-i639
        # library and we do not expect weird things to happen here
        if str(getattr(isolang, code_type)).lower() == lang.lower():
            iso_types.append(replace_types(code_type))

    lang_data = Lang(
        **{f"iso-639-{lang_}": getattr(isolang, f"pt{lang_}") for lang_ in ISO_LEVELS}
    )
    lang_data.update({"english": isolang.name, "iso_types": iso_types})

    if isolang.macro():
        return (
            lang_data,
            get_iso_lang_data(isolang.macro().name)[0],
        )  # first item in the returned tuple
    return lang_data, None


def find_language_names(query: str, lang_data: Lang | None = None) -> tuple[str, str]:
    """(native, english) language names for lang with help from lang_data

    Falls back to English name if available or query if not"""
    if lang_data is None:
        lang_data = get_language_details(query, failsafe=True)
        if not lang_data:
            return query, query

    try:
        query_locale = babel.Locale.parse(query)
        if native_display_name := query_locale.get_display_name():
            if english_display_name := query_locale.get_display_name("en"):
                return native_display_name, english_display_name
    except (babel.UnknownLocaleError, TypeError, ValueError, AttributeError):
        pass

    # ISO code lookup order matters (most qualified first)!
    for iso_level in [f"iso-639-{lang_}" for lang_ in reversed(ISO_LEVELS)]:
        try:
            query_locale = babel.Locale.parse(lang_data.get(iso_level))
            if native_display_name := query_locale.get_display_name():
                if english_display_name := query_locale.get_display_name("en"):
                    return native_display_name, english_display_name
        except (babel.UnknownLocaleError, TypeError, ValueError, AttributeError):
            pass
    default = lang_data.get("english") or query
    return default, default


def update_with_macro(lang_data: Lang, macro_data: Lang | None):
    """update empty keys from lang_data with ones of macro_data"""
    if macro_data:
        for key, value in macro_data.items():
            if key in lang_data and not lang_data.get(key):
                lang_data[key] = value
    return lang_data


def get_language_details(
    query: str, failsafe: bool | None = False  # noqa: FBT002
) -> Lang | None:
    """language details dict from query.

    When query fails, either raises NotFoundError or return None, based on failsafe

    """

    if query.isalpha() and (2 <= len(query) <= 3):  # noqa: PLR2004
        # possibility of iso-639 code
        adjusted_query = query
        native_query = query
        query_type = "purecode"
    elif all(x.isalpha() or x == "-" or x == "_" for x in query) and (
        query.count("_") + query.count("-") == 1
    ):
        # possibility of locale
        adjusted_query = re.split("-|_", query)[0]
        native_query = query.replace("-", "_")
        query_type = "locale"
    else:
        # possibility of iso language name
        adjusted_query = query.title().replace("Languages", "languages")
        native_query = query
        query_type = "languagename"

    try:
        lang_data, macro_data = get_iso_lang_data(adjusted_query)
    except NotFoundError as exc:
        if failsafe:
            return None
        raise exc

    iso_data = update_with_macro(lang_data, macro_data)
    native_name, english_name = find_language_names(native_query, iso_data)
    iso_data.update(
        {
            "english": english_name,
            "native": native_name,
            "querytype": query_type,
            "query": query,
        }
    )
    return iso_data


def is_valid_iso_639_3(code: str) -> bool:
    """whether code is a valid ISO-639-3 code"""
    return (get_language_details(code, failsafe=True) or {}).get("iso-639-3") == code
