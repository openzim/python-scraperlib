#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import locale
import gettext
import re
import babel

from iso639 import languages
from . import logger


class Locale:
    short = "en"
    name = "en_US.UTF-8"
    locale_dir = None
    domain = "messages"
    translation = gettext.translation("messages", fallback=True)

    @classmethod
    def setup(cls, locale_dir, locale_name):
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


def _(text):
    """ translates text according to setup'd locale """
    return Locale.translation.gettext(text)


def setlocale(root_dir, locale_name):
    """ set the desired locale for gettext.

        call this early """
    return Locale.setup(root_dir / "locale", locale_name)


def get_language_details(query):
    """ returns language details if query is a language or a locale otherwise returns None """

    def get_iso_lang_data(lang):
        """ return details if lang is a valid iso language else raises exception """

        code_types = ["part1", "part2b", "part2t", "part3", "part5", "name"]
        iso_types = []

        for code_type in code_types:
            try:
                languages.get(**{code_type: lang})
                iso_types.append(code_type)
            except KeyError:
                logger.debug(f"Not a valid {code_type}")

        if not iso_types:
            raise Exception("Not a valid iso language name/code")

        res = languages.get(**{iso_types[0]: lang})
        lang_data = {
            "iso-639-1": res.part1,
            "iso-639-2b": res.part2b,
            "iso-639-2t": res.part2t,
            "iso-639-3": res.part3,
            "iso-639-5": res.part5,
            "english": res.name,
            "iso_types": iso_types,
        }
        if res.macro:
            return (
                lang_data,
                get_iso_lang_data(res.macro)[0],
            )  # first item in the returned tuple
        return lang_data, None

    def find_native_name(query, lang_data, macro_data):
        try:
            return babel.Locale.parse(query).get_display_name()
        except (babel.UnknownLocaleError, TypeError, ValueError):
            logger.debug("Can't find native name from exact query")
        code_types = ["iso-639-5", "iso-639-3", "iso-639-2t", "iso-639-2b", "iso-639-1"]
        for code_type in code_types:
            try:
                return babel.Locale.parse(lang_data[code_type]).get_display_name()
            except (babel.UnknownLocaleError, TypeError, ValueError):
                logger.debug(f"Can't find native name from {code_type} of language")
        if macro_data:
            logger.debug("Trying the macrolanguage to find native name")
            for code_type in code_types:
                try:
                    return babel.Locale.parse(macro_data[code_type]).get_display_name()
                except (babel.UnknownLocaleError, TypeError, ValueError):
                    logger.debug(f"Can't find native name from {code_type} of language")
        return lang_data["english"]

    def combine_lang_and_macro_data(lang_data, macro_data):
        if macro_data:
            code_types = [
                "iso-639-1",
                "iso-639-2b",
                "iso-639-2t",
                "iso-639-3",
                "iso-639-5",
            ]
            for code_type in code_types:
                if not lang_data[code_type]:
                    lang_data[code_type] = macro_data[code_type]
        return lang_data

    if query.isalpha() and (2 <= len(query) <= 3):
        # possibility of iso-639 code
        try:
            lang_data, macro_data = get_iso_lang_data(query)
            iso_data = {
                "native": find_native_name(query, lang_data, macro_data),
                "querytype": "purecode",
            }
            iso_data.update(combine_lang_and_macro_data(lang_data, macro_data))
        except Exception as exc:
            logger.error(str(exc))
            return None

    elif all(x.isalpha() or x == "-" or x == "_" for x in query) and (
        query.count("_") + query.count("-") == 1
    ):
        # possibility of locale
        query_parts = re.split("-|_", query)
        try:
            lang_data, macro_data = get_iso_lang_data(query_parts[0])
            iso_data = {
                "native": find_native_name(
                    query.replace("-", "_"), lang_data, macro_data
                ),
                "querytype": "locale",
            }
            iso_data.update(combine_lang_and_macro_data(lang_data, macro_data))
        except Exception as exc:
            logger.error(str(exc))
            return None

    else:
        # possibility of iso language name
        try:
            lang_data, macro_data = get_iso_lang_data(
                query.title().replace("Languages", "languages")
            )
            iso_data = {
                "native": find_native_name(query, lang_data, macro_data),
                "querytype": "languagename",
            }
            iso_data.update(combine_lang_and_macro_data(lang_data, macro_data))
        except Exception as exc:
            logger.error(str(exc))
            return None

    iso_data["query"] = query
    return iso_data
