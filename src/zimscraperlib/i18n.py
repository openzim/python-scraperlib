from __future__ import annotations

import re

import babel
import iso639  # pyright: ignore[reportMissingTypeStubs]
import iso639.exceptions  # pyright: ignore[reportMissingTypeStubs]

ISO_LEVELS = ["1", "2b", "2t", "3", "5"]


class NotFoundError(ValueError):
    pass


class Lang:

    def __init__(self, requested_lang: str, iso639_lang_obj: iso639.Lang):
        self.iso_639_1 = iso639_lang_obj.pt1 or None
        self.iso_639_2b = iso639_lang_obj.pt2b or None
        self.iso_639_2t = iso639_lang_obj.pt2t or None
        self.iso_639_3 = iso639_lang_obj.pt3 or None
        self.iso_639_5 = iso639_lang_obj.pt5 or None
        self.english = iso639_lang_obj.name or None
        self.iso_types = [
            part_level
            for iso_level, part_level in [
                (f"pt{level}", f"part{level}") for level in ISO_LEVELS
            ]
            + [("name", "name")]
            if getattr(iso639_lang_obj, iso_level).lower() == requested_lang.lower()
        ]


class LangAndDetails:
    def __init__(
        self, lang: Lang, english_name: str, native: str, querytype: str, query: str
    ):
        self.iso_639_1 = lang.iso_639_1
        self.iso_639_2b = lang.iso_639_2b
        self.iso_639_2t = lang.iso_639_2t
        self.iso_639_3 = lang.iso_639_3
        self.iso_639_5 = lang.iso_639_5
        self.iso_types = lang.iso_types
        self.english = english_name
        self.native = native
        self.querytype = querytype
        self.query = query

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, LangAndDetails):
            return False

        return (
            self.iso_639_1 == value.iso_639_1
            and self.iso_639_2b == value.iso_639_2b
            and self.iso_639_2t == value.iso_639_2t
            and self.iso_639_3 == value.iso_639_3
            and self.iso_639_5 == value.iso_639_5
            and self.english == value.english
            and self.native == value.native
        )

    def __repr__(self) -> str:
        return (
            f"iso_639_1:{self.iso_639_1}, iso_639_2b:{self.iso_639_2b}, "
            f"iso_639_2t:{self.iso_639_2t}, iso_639_3:{self.iso_639_3}, "
            f"iso_639_5:{self.iso_639_5}, iso_639_5:{self.english}, "
            f"iso_639_5:{self.native}"
        )


def get_iso_lang_data(lang: str) -> tuple[Lang, Lang | None]:
    """ISO-639-x languages details for lang. Raises NotFoundError

    Returns a tuple (main_language, macro_language | None)"""

    try:
        isolang = iso639.Lang(lang)
    except (
        iso639.exceptions.InvalidLanguageValue,
        iso639.exceptions.DeprecatedLanguageValue,
    ) as exc:
        raise NotFoundError("Not a valid iso language name/code") from exc

    ourlang = Lang(lang, isolang)

    macro = isolang.macro()

    return (ourlang, get_iso_lang_data(macro.name)[0] if macro else None)


def find_language_names(
    query: str, lang_data: Lang | LangAndDetails | None = None
) -> tuple[str, str]:
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
    for iso_level in [f"iso_639_{level}" for level in reversed(ISO_LEVELS)]:
        try:
            query_locale = babel.Locale.parse(getattr(lang_data, iso_level))
            if native_display_name := query_locale.get_display_name():
                if english_display_name := query_locale.get_display_name("en"):
                    return native_display_name, english_display_name
        except (babel.UnknownLocaleError, TypeError, ValueError, AttributeError):
            pass
    default = lang_data.english or query
    return default, default


def update_with_macro(lang_data: Lang, macro_data: Lang | None):
    """update empty keys from lang_data with ones of macro_data"""
    if not macro_data:
        return lang_data

    for iso_level in [f"iso_639_{level}" for level in ISO_LEVELS]:
        if not getattr(lang_data, iso_level):
            setattr(lang_data, iso_level, getattr(macro_data, iso_level))

    return lang_data


def get_language_details(
    query: str, failsafe: bool | None = False  # noqa: FBT002
) -> LangAndDetails | None:
    """language details dict from query.

    When query fails, either raises NotFoundError or return None, based on failsafe

    """

    if query.isalpha() and (2 <= len(query) <= 3):  # noqa: PLR2004
        # possibility of iso-639 code
        adjusted_query = query
        native_query = query
        query_type = "purecode"
    elif all(x.isalpha() or x in ("-", "_") for x in query) and (
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
    return LangAndDetails(iso_data, english_name, native_name, query_type, query)


def is_valid_iso_639_3(code: str) -> bool:
    """whether code is a valid ISO-639-3 code"""
    lang = get_language_details(code, failsafe=True)
    return lang is not None and lang.iso_639_3 == code
