#!/usr/bin/env python3
# vim: ai ts=4 sts=4 et sw=4 nu

from __future__ import annotations

import gettext
import locale
import pathlib
import re

import babel
import iso639
import iso639.exceptions

ISO_LEVELS = ["1", "2b", "2t", "3", "5"]


class NotFound(ValueError):  # noqa: N818
    pass


class Locale:
    short = "en"
    name = "en_US.UTF-8"
    locale_dir = None
    domain = "messages"
    translation = gettext.translation("messages", fallback=True)

    @classmethod
    def setup(cls, locale_dir: pathlib.Path, locale_name: str):
        cls.name = locale_name
        cls.locale_dir = str(locale_dir)

        if "." in locale_name:
            cls.lang, cls.encoding = locale_name.split(".")
        else:
            cls.lang, cls.encoding = locale_name, "UTF-8"

        computed = locale.setlocale(locale.LC_ALL, (cls.lang, cls.encoding))

        gettext.bindtextdomain(cls.domain, cls.locale_dir)
        gettext.textdomain(cls.domain)

        cls.translation = gettext.translation(
            cls.domain, cls.locale_dir, languages=[cls.lang], fallback=True
        )
        return computed


def _(text: str) -> str:
    """translates text according to setup'd locale"""
    return Locale.translation.gettext(text)


def setlocale(root_dir: pathlib.Path, locale_name: str):
    """set the desired locale for gettext.

    call this early"""
    return Locale.setup(root_dir / "locale", locale_name)


def get_iso_lang_data(lang: str) -> tuple[dict, dict | None]:
    """ISO-639-x languages details for lang. Raises NotFound

    Included keys: iso-639-1, iso-639-2b, iso-639-2t, iso-639-3, iso-639-5
                   english, iso_types

    See get_language_details() for details"""

    iso_types = []

    try:
        isolang = iso639.Lang(lang)
    except (
        iso639.exceptions.InvalidLanguageValue,
        iso639.exceptions.DeprecatedLanguageValue,
    ) as exc:
        raise NotFound("Not a valid iso language name/code") from exc

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

    lang_data = {
        f"iso-639-{lang_}": getattr(isolang, f"pt{lang_}") for lang_ in ISO_LEVELS
    }
    lang_data.update({"english": isolang.name, "iso_types": iso_types})

    if isolang.macro():
        return (
            lang_data,
            get_iso_lang_data(isolang.macro().name)[0],
        )  # first item in the returned tuple
    return lang_data, None


def find_language_names(query: str, lang_data: dict | None = None) -> tuple[str, str]:
    """(native, english) language names for lang with help from language_details dict

    Falls back to English name if available or query if not"""
    if lang_data is None:
        lang_data = get_language_details(query, failsafe=True) or {}
    try:
        query_locale = babel.Locale.parse(query)
        return query_locale.get_display_name(), query_locale.get_display_name(
            "en"
        )  # pyright: ignore
    except (babel.UnknownLocaleError, TypeError, ValueError, AttributeError):
        pass

    # ISO code lookup order matters (most qualified first)!
    for iso_level in [f"iso-639-{lang_}" for lang_ in reversed(ISO_LEVELS)]:
        try:
            query_locale = babel.Locale.parse(lang_data.get(iso_level))
            return query_locale.get_display_name(), query_locale.get_display_name(
                "en"
            )  # pyright: ignore
        except (babel.UnknownLocaleError, TypeError, ValueError, AttributeError):
            pass
    default = lang_data.get("english", query)
    return default, default


def update_with_macro(lang_data: dict, macro_data: dict):
    """update empty keys from lang_data with ones of macro_data"""
    if macro_data:
        for key, value in macro_data.items():
            if key in lang_data and not lang_data[key]:
                lang_data[key] = value
    return lang_data


def get_language_details(
    query: str, failsafe: bool | None = False  # noqa: FBT002
) -> dict:
    """language details dict from query.

    Raises NotFound or return `und` language details if failsafe

    iso-639-1: str ISO-639-1 language code
    iso-639-2b: str ISO-639-2b language code
    iso-639-2t: str ISO-639-2t language code
    iso-639-3: str ISO-639-3 language code
    iso-639-5: str ISO-639-5 language code
    english: str language name in English
    native: str language name in is native language
    iso_types: [str] list of supported iso types

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
    except NotFound as exc:
        if failsafe:
            return None  # pyright: ignore
        raise exc

    iso_data = update_with_macro(lang_data, macro_data)  # pyright: ignore
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
