#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import locale
import gettext

import iso639


def setlocale(root_dir, locale_name):
    """ set the desired locale for gettext.

        call this early """
    computed = locale.setlocale(locale.LC_ALL, (locale_name.split(".")[0], "UTF-8"))
    gettext.bindtextdomain("messages", str(root_dir.joinpath("locale")))
    gettext.textdomain("messages")
    return computed


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
