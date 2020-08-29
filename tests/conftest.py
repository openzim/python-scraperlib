#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import pathlib

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--runslow", action="store_true", default=False, help="run slow tests"
    )
    parser.addoption(
        "--runinstalled",
        action="store_true",
        default=False,
        help="run tests checking for installed features",
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: mark test as slow to run")
    config.addinivalue_line(
        "markers", "installed: mark test as testing installed features"
    )


def pytest_collection_modifyitems(config, items):
    skip_slow = pytest.mark.skip(reason="need --runslow option to run")
    skip_installed = pytest.mark.skip(reason="need --runinstalled option to run")

    for item in items:
        if "installed" in item.keywords and not config.getoption("--runinstalled"):
            item.add_marker(skip_installed)
        if "slow" in item.keywords and not config.getoption("--runslow"):
            item.add_marker(skip_slow)


@pytest.fixture(scope="module")
def valid_http_url():
    return "http://google.com/favicon.ico"


@pytest.fixture(scope="module")
def valid_https_url():
    return "https://www.google.com/favicon.ico"


@pytest.fixture(scope="module")
def invalid_url():
    return "http://nodomain.notld/nofile.noext"


@pytest.fixture(scope="module")
def http_error_url():
    return "https://github.com/satyamtg/404_error"


@pytest.fixture(scope="module")
def timeout_url():
    # Should always fail with a connection timeout (nothing listening on that port)
    # taken from request's own tests
    return "http://10.255.255.1"


def file_src(fname):
    return pathlib.Path(__file__).parent.joinpath("files", fname)


@pytest.fixture(scope="module")
def png_image():
    return file_src("commons.png")


@pytest.fixture(scope="module")
def jpg_image():
    return file_src("pluto.jpg")


@pytest.fixture(scope="module")
def square_png_image():
    return file_src("square.png")


@pytest.fixture(scope="module")
def square_jpg_image():
    return file_src("square.jpg")


@pytest.fixture(scope="module")
def font():
    return file_src("DroidSans.ttf")


@pytest.fixture(scope="module")
def svg_image():
    return file_src("star.svg")


@pytest.fixture(scope="module")
def gif_image():
    return file_src("mail.gif")


@pytest.fixture(scope="module")
def webp_image():
    return file_src("whitewater.webp")
