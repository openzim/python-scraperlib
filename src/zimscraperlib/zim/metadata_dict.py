#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import collections
from typing import Union

from ..constants import ZIM_MANDATORY_METADATA_KEYS


class MetadataDict(collections.UserDict):
    """
    MetadataDict
        Convenient subclass of UserDict:
        - Determine if all mandatory Metadata are set.
    """

    @property
    def all_are_correct(self) -> bool:
        """
        Determine if the Key of all mandatory Metadata has a value.
        If they all have values, return True, otherwise return False.
        """
        lowercase_data_keys = [key.lower() for key in self.data.keys()]
        return all([key in lowercase_data_keys for key in ZIM_MANDATORY_METADATA_KEYS])
