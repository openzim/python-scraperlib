#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import pytest

from zimscraperlib.video import ConfigBuilder


@pytest.fixture(scope="function")
def config_builder():
    return ConfigBuilder()


@pytest.fixture(scope="function")
def hosted_media_links():
    return {
        "mp4": "https://github.com/satyamtg/test-bucket/raw/master/video.mp4",
        "mkv": "https://github.com/satyamtg/test-bucket/raw/master/video.mkv",
        "webm": "https://github.com/satyamtg/test-bucket/raw/master/video.webm",
        "mp3": "https://github.com/satyamtg/test-bucket/raw/master/audio.mp3",
    }
