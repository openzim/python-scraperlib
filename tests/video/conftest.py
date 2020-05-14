#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import pytest

from zimscraperlib.video import ConfigBuilder
from zimscraperlib.video.presets import VoiceMp3Low, VideoWebmLow


@pytest.fixture(scope="function")
def config_builder():
    return ConfigBuilder()

@pytest.fixture(scope="function")
def voice_mp3_low():
    return VoiceMp3Low()

@pytest.fixture(scope="function")
def video_webm_low():
    return VideoWebmLow()

@pytest.fixture(scope="function")
def hosted_video_links():
    links = {
        "mp4": "https://github.com/satyamtg/test-bucket/raw/master/video.mp4",
        "mkv": "https://github.com/satyamtg/test-bucket/raw/master/video.mkv",
    }
    return links
