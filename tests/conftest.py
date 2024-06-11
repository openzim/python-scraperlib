#!/usr/bin/env python3
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


@pytest.fixture(scope="module")
def png_image_url():
    return "https://commons.wikimedia.org/static/images/project-logos/commonswiki.png"


@pytest.fixture(scope="module")
def gzip_html_url():
    return "https://en.wikipedia.org/wiki/Main_Page"


@pytest.fixture(scope="module")
def gzip_nonhtml_url():
    return "http://mirror.download.kiwix.org/robots.txt"


def file_src(fname):
    return pathlib.Path(__file__).parent.joinpath("files", fname)


@pytest.fixture(scope="module")
def png_image():
    return file_src("commons48.png")


@pytest.fixture(scope="module")
def png_image2():
    return file_src("commons.png")


@pytest.fixture(scope="module")
def jpg_image():
    return file_src("pluto.jpg")


@pytest.fixture(scope="module")
def jpg_exif_image():
    return file_src("blue.jpg")


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
    return file_src("ninja.webp")


@pytest.fixture(scope="module")
def valid_user_agent():
    return "name/version (contact)"


@pytest.fixture(scope="session")
def small_zim_file(tmpdir_factory):
    from zimscraperlib.download import stream_file

    dst = tmpdir_factory.mktemp("data").join("small.zim")
    stream_file(
        "https://github.com/openzim/zim-testing-suite/raw/v0.3/data/nons/small.zim",
        dst,
    )
    return dst


@pytest.fixture(scope="session")
def ns_zim_file(tmpdir_factory):
    from zimscraperlib.download import stream_file

    dst = tmpdir_factory.mktemp("data").join("ns.zim")
    stream_file(
        "https://github.com/openzim/zim-testing-suite/raw/v0.4/data/withns/"
        "wikibooks_be_all_nopic_2017-02.zim",
        dst,
    )
    return dst


@pytest.fixture(scope="session")
def real_zim_file(tmpdir_factory):
    from zimscraperlib.download import stream_file

    dst = tmpdir_factory.mktemp("data").join("small.zim")
    stream_file(
        "https://github.com/openzim/zim-testing-suite/raw/v0.3/data/withns/"
        "wikipedia_en_climate_change_nopic_2020-01.zim",
        dst,
    )
    return dst


@pytest.fixture(scope="session")
def undecodable_byte_stream():
    """bytes that is not recognized by some libmagic and raises UnicodeDecodeError"""
    return (
        b"\x03\x04\x14\x00\x06\x00\x08\x00\x00\x00!\x00\xd9\x85nc\x81\x01\x00"
        b"\x00c\x04\x00\x00\x13\x00\x08\x02[Content_Types].xml \xa2\x04\x02("
        b"\xa0\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    )
