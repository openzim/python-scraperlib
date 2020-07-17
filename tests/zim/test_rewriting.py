#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import shutil
from pathlib import Path

import pytest

from zimscraperlib.zim.rewriting import (
    to_longurl,
    find_namespace_for,
    find_url,
    find_title_in,
    find_title_in_file,
    get_base64_src_of,
    relative_dots,
    fix_target_for,
    fix_file_target_for,
    fix_links_in_html,
    fix_links_in_html_file,
    fix_urls_in_css,
    fix_urls_in_css_file,
)


@pytest.mark.parametrize(
    "namespace, url, expected_longurl",
    [
        ("A", "test", "A/test"),
        ("I", "test", "I/test"),
        ("-", "test", "-/test"),
        ("M", "test", "M/test"),
        ("X", "test", "X/test"),
        # not used namespace
        ("B", "test", "B/test"),
    ],
)
def test_to_longurl(namespace, url, expected_longurl):
    assert to_longurl(namespace, url) == expected_longurl


@pytest.mark.parametrize(
    "mime_type, namespace",
    [
        ("text/html", "A"),
        ("", "-"),
        ("text/css", "-"),
        ("text/plain", "-"),
        ("text/javascript", "-"),
        ("application/json", "-"),
        ("application/octet-stream", "I"),
        ("image/png", "I"),
        ("kiwix", "I"),
    ],
)
def test_find_namespace_for(mime_type, namespace):
    assert find_namespace_for(mime_type) == namespace


@pytest.mark.parametrize(
    "path, mime_type, expected_longurl",
    [
        ("welcome", "text/html", "A/welcome"),
        ("welcome/to/hell", "text/html", "A/welcome/to/hell"),
        ("assets/style.css", "text/css", "-/assets/style.css"),
        ("i/m/g/pic.txt", "image/png", "I/i/m/g/pic.txt"),
    ],
)
def test_find_url(tmp_path, path, mime_type, expected_longurl):
    assert find_url(tmp_path, tmp_path / path, mime_type) == expected_longurl


def test_find_title(tmp_path, html_page):
    # find title in example HTML
    assert (
        find_title_in(html_page, "text/html")
        == "Kiwix lets you access free knowledge – even offline"
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
        == "Kiwix lets you access free knowledge – even offline"
    )
    # make sure non-HTML returns no title (from file)
    assert find_title_in_file(fpath, "text/plain") == ""
    # make sure incorrect filepath returns no title
    assert find_title_in_file(tmp_path / "nope", "text/html") == ""


def test_get_base64_src_of(tmp_path, png_image, jpg_image):
    # make sure we have proper format and mime types
    assert get_base64_src_of(png_image).startswith("data:image/png;base64,")
    assert get_base64_src_of(jpg_image).startswith("data:image/jpeg;base64,")
    # make sure we have correct alphabet
    get_base64_src_of(png_image).encode("ASCII")


@pytest.mark.parametrize(
    "root, path, expected_relative",
    [
        (None, "X/Y/Z", "../../"),
        (None, "file", "/"),
        (".", "file", "/"),
        (".", "folder/file", "../"),
        (".", "A/welcome", "../"),
    ],
)
def test_relative_dots(tmp_path, root, path, expected_relative):
    if root:
        assert relative_dots(Path(root), Path(path)) == expected_relative
    else:
        assert relative_dots(tmp_path, tmp_path.joinpath(path)) == expected_relative


def test_fix_target_for(tmp_path, monkeypatch):
    # make sure target in dangling source is correctly fixed
    assert (
        fix_target_for(Path("."), Path("A/welcome"), Path("files/dl.pdf"))
        == "../I/files/dl.pdf"
    )
    # make sure target to a file is fixed when not checking existence
    assert (
        fix_file_target_for(tmp_path, "home.html", "files/dl.pdf", False)
        == "../I/files/dl.pdf"
    )
    # make sure target is NOT fixed when target is not present and we requested it to
    assert (
        fix_file_target_for(tmp_path, "home.html", "files/dl.pdf", True)
        == "files/dl.pdf"
    )
    # make sure target to a file is fixed when checking existence and is present
    ff = Path(tmp_path / "files")
    ff.mkdir()
    ff.joinpath("dl.pdf").touch()
    assert (
        fix_file_target_for(tmp_path, "home.html", "files/dl.pdf", True)
        == "../I/files/dl.pdf"
    )
    # special behavior when CWD is /
    monkeypatch.chdir("/")
    assert (
        fix_target_for(
            Path("."), Path("A/home.html"), Path("assets/chosen/chosen.min.css")
        )
        == "../-/assets/chosen/chosen.min.css"
    )


@pytest.mark.parametrize(
    "pattern, expected_count", [("../A/", 2), ("../I/", 2), ("../-/", 2)],
)
def test_fix_links_in_html(html_str, pattern, expected_count):
    assert fix_links_in_html("A/welcome", html_str).count(pattern) == expected_count


def test_fix_links_in_html_file(tmp_path, html_str):
    # make sure we raise on missing param (url or root mandatory)
    with pytest.raises(ValueError):
        fix_links_in_html_file(tmp_path)

    # make sure we raise on non-HTML file (folder here)
    fpath = tmp_path / "test.html"
    with pytest.raises(FileNotFoundError):
        fix_links_in_html_file(fpath, url="A/home")

    with open(fpath, "w") as fh:
        fh.write(html_str)

    # ensure we don't modify source when not using in_place
    fix_links_in_html_file(fpath, url="A/home")
    with open(fpath, "r") as fh:
        assert fh.read() == html_str

    # with root instead of url
    # ensure we don't modify source when not in in_place
    fix_links_in_html_file(fpath, root=tmp_path)
    with open(fpath, "r") as fh:
        assert fh.read() == html_str

    # ensure we're rewriting source with in_place
    fix_links_in_html_file(fpath, url="A/home", in_place=True)
    with open(fpath, "r") as fh:
        assert fh.read() != html_str


@pytest.mark.parametrize(
    "pattern, expected_count", [("../A/", 2), ("../I/", 2), ("../-/", 2)],
)
def test_fix_links_in_html_file2(html_file, pattern, expected_count):
    # make sure not-in place rewrites properly
    assert (
        fix_links_in_html_file(html_file, url="A/home").count(pattern) == expected_count
    )

    # make sure in_place rewrites properly
    fix_links_in_html_file(html_file, root=html_file.parent, in_place=True)
    with open(html_file, "r") as fh:
        assert fh.read().count(pattern) == expected_count


@pytest.mark.parametrize(
    "pattern, expected_count", [("../A/", 0), ("../I/", 24), ("../-/", 0)],
)
def test_fix_urls_in_css(css_str, pattern, expected_count):
    assert fix_urls_in_css("-/test.css", css_str).count(pattern) == expected_count


def test_fix_urls_in_css_down(css_str_down):
    assert (
        fix_urls_in_css("-/assets/test.css", css_str_down).count("../../I/sample.jpg")
        == 1
    )


def test_fix_urls_in_css_file(tmp_path, css_str, font, css_str_with_fonts):
    # make sure we raise on missing param (url or root mandatory)
    with pytest.raises(ValueError):
        fix_urls_in_css_file(tmp_path)

    fpath = tmp_path / "test.css"

    # make sure we raise on non-CSS file
    with pytest.raises(FileNotFoundError):
        fix_urls_in_css_file(fpath, url="-/test.css")

    with open(fpath, "w") as fh:
        fh.write(css_str)

    # ensure we don't modify source when not in in_place
    fix_urls_in_css_file(fpath, url="-/test.css")
    with open(fpath, "r") as fh:
        assert fh.read() == css_str

    # with root instead of url
    # ensure we don't modify source when not in in_place
    fix_urls_in_css_file(fpath, root=tmp_path)
    with open(fpath, "r") as fh:
        assert fh.read() == css_str

    # ensure url to font are converted to data:
    font_dir = tmp_path / "font"
    font_dir.mkdir()
    with open(fpath, "w") as fh:
        fh.write(css_str_with_fonts)
    shutil.copyfile(font, font_dir / "DroidSans.ttf")
    fix_urls_in_css_file(fpath, url="-/test.css", in_place=True)
    with open(fpath, "r") as fh:
        content = fh.read()
        assert content != css_str
        assert content.count("data:") == 12


@pytest.mark.parametrize(
    "pattern, expected_count", [("../A/", 0), ("../I/", 24), ("../-/", 0)],
)
def test_fix_urls_in_css_file2(css_file, pattern, expected_count):
    # make sure not-in place rewrites properly
    assert fix_urls_in_css_file(css_file, url="A/home").count(pattern) == expected_count

    # make sure in_place rewrites properly
    fix_urls_in_css_file(css_file, root=css_file.parent, in_place=True)
    with open(css_file, "r") as fh:
        assert fh.read().count(pattern) == expected_count
