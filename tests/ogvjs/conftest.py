#!/usr/bin/env python3
# vim: ai ts=4 sts=4 et sw=4 nu

import pytest


@pytest.fixture(scope="module")
def videojs_url():
    return (
        "https://github.com/videojs/video.js/releases/download/v7.6.4/"
        "video-js-7.6.4.zip"
    )


@pytest.fixture(scope="module")
def ogvjs_url():
    return "https://github.com/brion/ogv.js/releases/download/1.6.1/ogvjs-1.6.1.zip"


@pytest.fixture(scope="module")
def videojs_ogvjs_url():
    return "https://github.com/hartman/videojs-ogvjs/archive/v1.3.1.zip"
