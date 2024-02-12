#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 nu

import pytest

from zimscraperlib.types import ARTICLE_MIME, FONT_MIMES, get_mime_for_name


def test_constants():
    assert ARTICLE_MIME == "text/html"
    all_fonts = "".join(FONT_MIMES)
    for key in ("ttf", "woff", "woff2", "opentype"):
        assert key in all_fonts


@pytest.mark.parametrize(
    "filename, expected_mime, fallback, no_ext_to",
    [
        ("hello.html", "text/html", None, None),
        ("some picture.png", "image/png", None, None),
        # make sure we get default fallback on error
        (b"-", "application/octet-stream", None, None),
        # make sure fallback is not returned on success
        ("hello.html", "text/html", "text/plain", None),
        # make sure fallback is returned on missing
        ("hello.zzz", "text/plain", "text/plain", None),
        # make sure no-extension returns HTML
        ("hello/", "text/html", None, None),
        ("welcome", "text/html", None, None),
        # make sure no-extension returns not_ext_to
        ("hello/", "image/png", None, "image/png"),
        ("welcome", "text/css", None, "text/css"),
        # make sure WASM are properly retuned
        ("assets/ogv.wasm", "application/wasm", None, None),
        # make sure our custom mapping is used
        ("assets/subtite.vtt", "text/vtt", None, None),
        (
            "assets/jquery.min.js",
            ("application/javascript", "text/javascript"),
            None,
            None,
        ),
        ("assets/test.css", "text/css", None, None),
    ],
)
def test_mime_for_name(filename, fallback, expected_mime, no_ext_to):
    kwargs = {}
    if fallback is not None:
        kwargs.update({"fallback": fallback})
    if no_ext_to is not None:
        kwargs.update({"no_ext_to": no_ext_to})
    if isinstance(expected_mime, tuple):
        assert get_mime_for_name(filename, **kwargs) in expected_mime
    else:
        assert get_mime_for_name(filename, **kwargs) == expected_mime
