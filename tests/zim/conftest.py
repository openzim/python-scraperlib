#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import pytest

from zimscraperlib.zim import ZimInfo


@pytest.fixture(scope="function")
def ziminfo():
    return ZimInfo()
