#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import pytest
import pathlib

from zimscraperlib.video import VidCompressionCfg, VidUtil


@pytest.fixture(scope="function")
def vidcompressioncfg():
    return VidCompressionCfg()


@pytest.fixture(scope="function")
def vidutil():
    return VidUtil(VidCompressionCfg(), "mp4", True)


@pytest.fixture(scope="function")
def temp_video_dir():
    return pathlib.Path(__file__).parent.joinpath("temp")


@pytest.fixture(scope="function")
def hosted_video_links():
    links = {
        "mp4": "https://github.com/satyamtg/test-bucket/raw/master/video.mp4",
        "mkv": "https://github.com/satyamtg/test-bucket/raw/master/video.mkv",
    }
    return links
