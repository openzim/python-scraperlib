#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import collections
import datetime

from ..constants import DEFAULT_LANG_ISO_639_3, ZIM_MANDATORY_METADATA_KEYS
from ..i18n import get_iso_lang_data

"""MetadataDict
   Convenient subclass of UserDict:
   - Automatic initialization of all mandatory Metadata.
   - Determine if all mandatory Metadata are set."""


class MetadataDict(collections.UserDict):
    def __init__(self):
        super().__init__()
        default_data = {key: "" for key in ZIM_MANDATORY_METADATA_KEYS}
        fix_default_data = {
            "Language": DEFAULT_LANG_ISO_639_3,
            "Date": datetime.datetime.today(),
        }
        default_data.update(fix_default_data)
        self.update(default_data)

    def __setitem__(self, key, item):
        super().__setitem__(key.capitalize(), item)

    def update(self, dict):
        dict = {key.capitalize(): value for key, value in dict.items()}
        super().update(dict)

    def __check_languages_type(self):
        languages_iso_639_3 = self.get("Language", default="").split(",")
        for language in languages_iso_639_3:
            get_iso_lang_data(language)

    def __check_date_type(self):
        content = self.get("Date", default="")
        if not isinstance(content, (datetime.date, datetime.datetime)):
            date.fromisoformat(content)

    def check_values_type(self):
        self.__check_languages_type()
        self.__check_date_type()

    @property
    def mandatory_values_all_set(self):
        if any([not self.data[key] for key in ZIM_MANDATORY_METADATA_KEYS]):
            return False
        return True

    @property
    def unset_keys(self):
        return [key for key, value in self.data.items() if not value]
