#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 nu

import io

import pytest

from zimscraperlib.zim._libkiwix import getline
from zimscraperlib.zim._libkiwix import parseMimetypeCounter as parse  # noqa: N813

empty = {}


def test_geline_nodelim():
    string = "text/javascript=8;text/html=3;application/warc-headers=28364;"
    ins = io.StringIO(string)
    assert getline(ins) == (True, string)


def test_getline():
    ins = io.StringIO("text/javascript=8;text/html=3;application/warc-headers=28364;")
    assert getline(ins, ";") == (False, "text/javascript=8")  # pyright: ignore
    assert getline(ins, ";") == (False, "text/html=3")  # pyright: ignore
    assert getline(ins, ";") == (  # pyright: ignore
        False,
        "application/warc-headers=28364",
    )
    assert getline(ins, ";") == (True, "")  # pyright: ignore


@pytest.mark.parametrize(
    "counter_str, counter_map",
    [
        ("", empty),
        ("foo=1", {"foo": 1}),
        ("foo=1;text/html=50;", {"foo": 1, "text/html": 50}),
        ("text/html;raw=true=1", {"text/html;raw=true": 1}),
        (
            "foo=1;text/html;raw=true=50;bar=2",
            {"foo": 1, "text/html;raw=true": 50, "bar": 2},
        ),
        (
            "text/html=3;application/warc-headers=28364;"
            "text/html;raw=true=6336;text/css=47;text/javascript=98;image/png=968;"
            "image/webp=24;application/json=3694;image/gif=10274;image/jpeg=1582;"
            "font/woff2=25;text/plain=284;application/atom+xml=247;"
            "application/x-www-form-urlencoded=9;video/mp4=9;"
            "application/x-javascript=7;application/xml=1;image/svg+xml=5",
            {
                "text/html": 3,
                "application/warc-headers": 28364,
                "text/html;raw=true": 6336,
                "text/css": 47,
                "text/javascript": 98,
                "image/png": 968,
                "image/webp": 24,
                "application/json": 3694,
                "image/gif": 10274,
                "image/jpeg": 1582,
                "font/woff2": 25,
                "text/plain": 284,
                "application/atom+xml": 247,
                "application/x-www-form-urlencoded": 9,
                "video/mp4": 9,
                "application/x-javascript": 7,
                "application/xml": 1,
                "image/svg+xml": 5,
            },
        ),
        ("text/html", empty),
        ("text/html=", empty),
        ("text/html=0", {"text/html": 0}),
        ("text/html=foo", empty),
        ("text/html=123foo", empty),
        ("text/html=50;foo", {"text/html": 50}),
        ("text/html;foo=20", empty),
        ("text/html;foo=20;", empty),
        ("text/html=50;;foo", {"text/html": 50}),
    ],
)
def test_counter_parsing(counter_str, counter_map):
    # https://github.com/kiwix/libkiwix/blob/master/test/counterParsing.cpp
    assert parse(counter_str) == counter_map
