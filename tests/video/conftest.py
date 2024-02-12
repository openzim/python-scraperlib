#!/usr/bin/env python3
# vim: ai ts=4 sts=4 et sw=4 nu

import pathlib

import pytest


@pytest.fixture(scope="function")
def test_files():
    files_dir = pathlib.Path(__file__).parent.parent.joinpath("files")
    return {
        "mp4": files_dir.joinpath("video.mp4"),
        "mkv": files_dir.joinpath("video.mkv"),
        "webm": files_dir.joinpath("video.webm"),
        "mp3": files_dir.joinpath("audio.mp3"),
    }
