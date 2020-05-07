#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import locale
import gettext

import iso639


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


def get_language_details(iso_639_3):
    """ dict container iso639-2, name and native name for an iso-639-3 code """
    non_iso_langs = {
        "zh-Hans": {
            "code": "zh-Hans",
            "iso-639-1": "zh",
            "english": "Simplified Chinese",
            "native": "简化字",
        },
        "zh-Hant": {
            "code": "zh-Hant",
            "iso-639-1": "zh",
            "english": "Traditional Chinese",
            "native": "正體字",
        },
        "iw": {"code": "iw", "iso-639-1": "he", "english": "Hebrew", "native": "עברית"},
        "es-419": {
            "code": "es-419",
            "iso-639-1": "es-419",
            "english": "Spanish",
            "native": "Español",
        },
        "multi": {
            "code": "mul",
            "iso-639-1": "en",
            "english": "Multiple Languages",
            "native": "Multiple Languages",
        },
    }

    try:
        return (
            non_iso_langs.get(iso_639_3)
            if iso_639_3 in non_iso_langs.keys()
            else {
                "code": iso_639_3,
                "iso-639-1": iso639.to_iso639_1(iso_639_3),
                "english": iso639.to_name(iso_639_3),
                "native": iso639.to_native(iso_639_3),
            }
        )
    except iso639.NonExistentLanguageError:
        return {
            "code": iso_639_3,
            "iso-639-1": iso_639_3,
            "english": iso_639_3,
            "native": iso_639_3,
        }
