#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import locale
import gettext
import re

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
    """returns language details if query is a language or a locale otherwise returns None"""

    def get_iso_lang_data(lang):
        """return details if lang is a valid iso language else raises exception"""

        iso_types = []
        try:
            languages.get(part1=lang)
            iso_types.append("part1")
        except KeyError:
            logger.debug("Not a valid iso-639-1")
        try:
            languages.get(part2b=lang)
            iso_types.append("part2b")
        except KeyError:
            logger.debug("Not a valid iso-639-2b")
        try:
            languages.get(part2t=lang)
            iso_types.append("part2t")
        except KeyError:
            logger.debug("Not a valid iso-639-2t")
        try:
            languages.get(part3=lang)
            iso_types.append("part3")
        except KeyError:
            logger.debug("Not a valid iso-639-3")
        try:
            languages.get(part5=lang)
            iso_types.append("part5")
        except KeyError:
            logger.debug("Not a valid iso-639-5")
        try:
            languages.get(name=lang)
            iso_types.append("name")
        except KeyError:
            logger.debug("Not a valid iso language name")

        if not iso_types:
            raise Exception("Not a valid iso language name/code")

        res = languages.get(**{iso_types[0]: lang})

        return {
            "iso-639-1": res.part1,
            "iso-639-2b": res.part2b,
            "iso-639-2t": res.part2t,
            "iso-639-3": res.part3,
            "iso-639-5": res.part5,
            "english": res.name,
            "iso_types": iso_types,
        }

    if query.isalpha() and (2 <= len(query) <= 3):
        # possibility of iso-639 code
        try:
            iso_data = get_iso_lang_data(query)
            iso_data["querytype"] = "purecode"
        except Exception as exc:
            logger.error(str(exc))
            return None

    elif all(x.isalpha() or x == "-" or x == "_" for x in query) and (
        query.count("_") + query.count("-") == 1
    ):
        # possibility of locale
        query_parts = re.split("-|_", query)
        try:
            iso_data = get_iso_lang_data(query_parts[0])
            iso_data["querytype"] = "locale"
        except Exception as exc:
            logger.error(str(exc))
            return None

    else:
        # possibility of iso language name
        try:
            iso_data = get_iso_lang_data(
                query.title().replace("Languages", "languages")
            )
            iso_data["querytype"] = "languagename"
        except Exception as exc:
            logger.error(str(exc))
            return None

    iso_data["query"] = query
    return iso_data
