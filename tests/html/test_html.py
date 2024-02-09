#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 nu

import pytest

from zimscraperlib.html import (
    find_language_in,
    find_language_in_file,
    find_title_in,
    find_title_in_file,
)


def test_find_title(tmp_path, html_page):
    # find title in example HTML
    assert (
        find_title_in(html_page, "text/html")
        == "Kiwix lets you access free knowledge - even offline"
    )
    # make sure non-HTML returns no title
    assert find_title_in(html_page, "text/plain") == ""
    # make sure non-html, even if using html mime returns no title
    assert find_title_in("title: Kiwix", "text/html") == ""

    # find title in local file
    fpath = tmp_path / "test.html"
    with open(fpath, "w") as fh:
        fh.write(html_page)
    assert (
        find_title_in_file(fpath, "text/html")
        == "Kiwix lets you access free knowledge - even offline"
    )
    # make sure non-HTML returns no title (from file)
    assert find_title_in_file(fpath, "text/plain") == ""
    # make sure incorrect filepath returns no title
    assert find_title_in_file(tmp_path / "nope", "text/html") == ""


def test_find_language(tmp_path, html_page):
    # find language in example HTML
    assert find_language_in(html_page, "text/html") == "en-US"
    # make sure non-HTML returns no language
    assert find_language_in(html_page, "text/plain") == ""
    # make sure non-html, even if using html mime returns no language
    assert find_language_in("lang: en-US", "text/html") == ""
    # make sure meta without http-equiv="content-language" returns no language
    assert (
        find_language_in(
            "<html><head><meta content='en-UK'></head><body></body></html>", "text/html"
        )
        == ""
    )

    # find language in local file
    fpath = tmp_path / "test.html"
    with open(fpath, "w") as fh:
        fh.write(html_page)
    assert find_language_in_file(fpath, "text/html") == "en-US"
    # make sure non-HTML returns no language (from file)
    assert find_language_in_file(fpath, "text/plain") == ""
    # make sure incorrect filepath returns no language
    assert find_language_in_file(tmp_path / "nope", "text/html") == ""


@pytest.mark.parametrize(
    "html_string, expected_language",
    [
        (
            "<html lang='en-US' xml:lang='zh-CN'><head>"
            "<meta http-equiv='content-language' content='en-UK'></head>"
            "<body lang='hi-IN'></body></html>",
            "en-US",
        ),
        (
            "<html xml:lang='en-US'><head>"
            "<meta http-equiv='content-language' content='en-UK'></head>"
            "<body lang='hi-IN'></body></html>",
            "en-US",
        ),
        (
            "<html><head><meta http-equiv='content-language' content='en-UK'>"
            "</head><body lang='hi-IN'></body></html>",
            "hi-IN",
        ),
        (
            "<html><head><meta http-equiv='content-language' content='en-UK'>"
            "</head><body></body></html>",
            "en-UK",
        ),
    ],
)
def test_find_language_order(html_string, expected_language):
    assert find_language_in(html_string, "text/html") == expected_language
