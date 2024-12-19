import re

import babel
import iso639  # pyright: ignore[reportMissingTypeStubs]
import iso639.exceptions  # pyright: ignore[reportMissingTypeStubs]

ISO_LEVELS = ["1", "2b", "2t", "3", "5"]


class NotFoundError(ValueError): ...


class Language:
    """Qualified ISO-639-3 language"""

    def __init__(self, query: str):
        """Instantiate a valid ISO-639-3 Language from query

        params: either an ISO-639 code or a locale or an english language name"""
        self.iso_639_1: str | None = None
        self.iso_639_2b: str | None = None
        self.iso_639_2t: str | None = None
        self.iso_639_3: str | None = None
        self.iso_639_5: str | None = None
        self.english: str | None = None
        self.native: str | None = None
        self.iso_types: list[str] = []
        self.query: str = query
        self.native_query: str | None = None
        self.querytype: str | None = None

        def get_adjusted_query(query: str) -> tuple[str, str, str]:
            # possibily an iso-639 code
            if query.isalpha() and (2 <= len(query) <= 3):  # noqa: PLR2004
                adjusted_query = query
                native_query = query
                query_type = "purecode"
            # possibily a locale
            elif all(x.isalpha() or x in ("-", "_") for x in query) and (
                query.count("_") + query.count("-") == 1
            ):
                adjusted_query = re.split("-|_", query)[0]
                native_query = query.replace("-", "_")
                query_type = "locale"
            # possibily an ISO language name
            else:
                adjusted_query = query.title().replace("Languages", "languages")
                native_query = query
                query_type = "languagename"
            return adjusted_query, native_query, query_type

        adjusted_query, self.native_query, self.querytype = get_adjusted_query(query)

        try:
            isolang = iso639.Lang(adjusted_query)
        except (
            iso639.exceptions.InvalidLanguageValue,
            iso639.exceptions.DeprecatedLanguageValue,
        ) as exc:
            raise NotFoundError("Not a valid iso language name/code") from exc

        parts_keys_map = {
            "iso_639_1": "pt1",
            "iso_639_2b": "pt2b",
            "iso_639_2t": "pt2t",
            "iso_639_3": "pt3",
            "iso_639_5": "pt5",
            "english": "name",
        }

        self.iso_639_1 = isolang.pt1 or None
        self.iso_639_2b = isolang.pt2b or None
        self.iso_639_2t = isolang.pt2t or None
        self.iso_639_3 = isolang.pt3 or None
        self.iso_639_5 = isolang.pt5 or None
        self.english = isolang.name or None
        self.iso_types = [
            part_level
            for iso_level, part_level in [
                (f"pt{level}", f"part{level}") for level in ISO_LEVELS
            ]
            + [("name", "name")]
            if getattr(isolang, iso_level).lower() == adjusted_query.lower()
        ]

        # update if language has a macro
        if isolang.macro():
            for iso_level in [f"iso_639_{level}" for level in ISO_LEVELS]:
                if not getattr(self, iso_level):
                    setattr(
                        self,
                        iso_level,
                        # we'll get the pt attr for each iso_xxx
                        getattr(isolang.macro(), parts_keys_map[iso_level], None)
                        # we want None if value is empty
                        or None,
                    )

        self.native, self.english = self._get_names_from(self.native_query)

    def _get_names_from(self, query: str) -> tuple[str, str]:
        """logic to find language names from babel and fallback"""
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
                query_locale = babel.Locale.parse(getattr(self, iso_level))
                if native_display_name := query_locale.get_display_name():
                    if english_display_name := query_locale.get_display_name("en"):
                        return native_display_name, english_display_name
            except (
                babel.UnknownLocaleError,
                TypeError,
                ValueError,
                AttributeError,
            ):
                pass
        default = self.english or query
        return default, default

    def todict(self) -> dict[str, str | None | list[str]]:
        return {
            key.replace("_", "-") if key.startswith("iso") else key: getattr(
                self, key, None
            )
            for key in [
                "iso_639_1",
                "iso_639_2b",
                "iso_639_2t",
                "iso_639_3",
                "iso_639_5",
                "english",
                "iso_types",
                "native",
                "querytype",
                "query",
            ]
        }

    def __repr__(self) -> str:
        data_repr = ", ".join(
            f'{key.replace("-", "_")}="{value}"' for key, value in self.todict().items()
        )
        return f"{type(self).__name__}({data_repr})"

    def __str__(self) -> str:
        return f"{self.iso_639_3}: {self.english}"

    def __eq__(self, value: object) -> bool:
        return (
            self.iso_639_1 == getattr(value, "iso_639_1", None)
            and self.iso_639_2b == getattr(value, "iso_639_2b", None)
            and self.iso_639_2t == getattr(value, "iso_639_2t", None)
            and self.iso_639_3 == getattr(value, "iso_639_3", None)
            and self.iso_639_5 == getattr(value, "iso_639_5", None)
            and self.english == getattr(value, "english", None)
            and self.native == getattr(value, "native", None)
        )


def find_language_names(query: str) -> tuple[str, str]:
    """(native, english) language names for query"""
    try:
        lang = Language(query)
    except NotFoundError:
        return query, query
    # should be qualified but "None" is as valid as anything if not
    return str(lang.native), str(lang.english)


def get_language(lang_code: str) -> Language:
    """Language from lang_code"""
    return Language(lang_code)


def get_language_or_none(lang_code: str) -> Language | None:
    """Language from lang_code or None if not found"""
    try:
        return get_language(lang_code)
    except NotFoundError:
        return None


def is_valid_iso_639_3(code: str) -> bool:
    """whether code is a valid ISO-639-3 code"""
    lang = get_language_or_none(code)
    return lang is not None and lang.iso_639_3 == code
