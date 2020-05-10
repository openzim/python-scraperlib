#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import pytest

from zimscraperlib.video import VidCompressionCfg, VidUtil


@pytest.fixture(scope="function")
def vidcompressioncfg():
    return VidCompressionCfg()


@pytest.fixture(scope="function")
def vidutil():
    return VidUtil(VidCompressionCfg(), "mp4", True)
