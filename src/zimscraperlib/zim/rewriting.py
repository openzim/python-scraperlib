#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

""" Tools to rewrite Zim Articles

    Conversion from existing links to Zim-compatible links (namespace-aware) might
    be required for existing contents. Following tools helps automate this as much
    as possible. """

import re
import base64
import urllib
import pathlib
from typing import Union, BinaryIO, TextIO, Optional

from bs4 import BeautifulSoup

from ..filesystem import get_file_mimetype
from ..types import get_mime_for_name, ARTICLE_MIME, FONT_MIMES


def to_longurl(namespace: str, url: str) -> str:
    """ Namespace-aware URL from a namespace and url """
    return f"{namespace}/{url}"


def find_namespace_for(mime_type: str) -> str:
    """ Suggested namespace for a mime-type """
    if mime_type == ARTICLE_MIME:
        return "A"
    if (
        not mime_type
        or mime_type.startswith("text/")
        or mime_type in FONT_MIMES + ["application/javascript", "application/json"]
    ):
        return "-"
    return "I"


def find_url(root: pathlib.Path, fpath: pathlib.Path, mime_type: str) -> str:
    """ Suggested url for a file, including its namespace """
    return f"{find_namespace_for(mime_type)}/{fpath.relative_to(root)}"


def find_title_in(content: Union[str, BinaryIO, TextIO], mime_type: str) -> str:
    """Extracted title from HTML content

    blank on failure to extract and non-HTML files"""
    if mime_type != ARTICLE_MIME:
        return ""
    try:
        return BeautifulSoup(content, "lxml").find("title").text
    except Exception:
        return ""


def find_title_in_file(fpath: pathlib.Path, mime_type: str) -> str:
    """ Extracted title from an HTML file """
    try:
        with open(fpath, "r") as fh:
            return find_title_in(fh, mime_type)
    except Exception:
        return ""


def find_language_in(content: Union[str, BinaryIO, TextIO], mime_type: str) -> str:
    """Extracted language from HTML content

    blank on failure to extract and non-HTML files"""
    if mime_type != ARTICLE_MIME:
        return ""
    mapping = {"html": ["lang", "xml:lang"], "body": ["lang"], "meta": ["content"]}
    soup = BeautifulSoup(content, "lxml")
    for nodename, keylist in mapping.items():
        for key in keylist:
            node = soup.find(nodename)
            if node:
                if not node.has_attr(key):
                    continue
                if (
                    nodename == "meta"
                    and not node.attrs.get("http-equiv", "").lower()
                    == "content-language"
                ):
                    continue
                return node.attrs[key]
    return ""


def find_language_in_file(fpath: pathlib.Path, mime_type: str) -> str:
    """ Extracted language from an HTML file """
    try:
        with open(fpath, "r") as fh:
            return find_language_in(fh, mime_type)
    except Exception:
        return ""


def get_base64_src_of(fpath: pathlib.Path, mime_type: Optional[str] = None) -> str:
    """ HTML/CSS source data string representing fpath (data:{type};base64,xxx) """
    if not mime_type:
        mime_type = get_file_mimetype(fpath)

    with open(fpath, "rb") as fh:
        return (
            f"data:{mime_type};base64,"
            f"{base64.standard_b64encode(fh.read()).decode('ASCII')}"
        )


def relative_dots(root: pathlib.Path, source: pathlib.Path) -> str:
    """ Path-like prefix from a source path/url to a root """
    depth_source = len(source.parent.relative_to(root).parts)  # was not parent
    return "/".join([".."] * depth_source) + "/"


def fix_target_for(
    root: pathlib.Path, source: pathlib.Path, target: pathlib.Path
) -> str:
    """ Fixed link from source to target: relative and namespace aware """

    # remove namespace from source ; and join it with target
    flat_target = pathlib.Path(*source.parts[1:]).parent.joinpath(target)

    if str(root.resolve()) == "/":
        flat_target = flat_target.relative_to(root)
    else:
        # resolve relative links and back to relative from resolved
        flat_target = flat_target.resolve().relative_to(root.resolve())

    return relative_dots(root, source) + find_url(
        root, flat_target, get_mime_for_name(target)
    )


def fix_file_target_for(
    root: pathlib.Path, source: pathlib.Path, target: pathlib.Path, require_target: bool
) -> str:
    """fixed link from source to target: relative and namespace aware

    Links to non-local file targets are kept as-is if require_target is set"""
    fpath = root / target
    if require_target and not fpath.exists():
        return str(target)

    return fix_target_for(
        pathlib.Path("."),
        pathlib.Path(find_url(root, root / source, get_mime_for_name(root / source))),
        target,
    )


def fix_links_in_html(url: str, content: str) -> str:
    """HTML with all links fixed to namespace-aware ones

    - url: target URL of this HTML in ZIM (with namespace)
    - content: HTML text to rewrite"""
    mapping = {
        "link": "href",
        "a": "href",
        "script": "src",
        "source": "src",
        "img": "src",
        "track": "src",
        "video": "poster",
        "audio": "poster",
        "object": "data",
    }
    soup = BeautifulSoup(content, "lxml")
    for nodename, key in mapping.items():
        for node in soup.find_all(nodename):

            # do nothing if the required attribute is not found in the tag
            if not node.has_attr(key):
                continue

            html_link = node.attrs[key]

            # parse as a URL to extract querystring and fragment
            scheme, netloc, target, query, fragment = urllib.parse.urlsplit(html_link)

            # do nothing for links with netloc and special schemes (mailto, tel, etc)
            if netloc or scheme:
                continue

            # use source as target if there's none
            if not target:
                target = pathlib.Path(url).name  # only the filename

            fixed = fix_target_for(
                pathlib.Path("."), pathlib.Path(url), pathlib.Path(target)
            )

            if query or fragment:
                fixed = urllib.parse.urlunsplit(("", "", fixed, query, fragment))

            node.attrs[key] = fixed
    return str(soup)


def fix_links_in_html_file(
    fpath: pathlib.Path,
    url: Optional[str] = None,
    root: Optional[pathlib.Path] = None,
    in_place: Optional[bool] = False,
) -> Union[str, None]:
    """HTML with all links fixed to namespace-aware ones

    - url: target URL of this HTML in ZIM (with namespace)
    - root: root folder of content (to guess url from)
    One of `url` or `root` is required
    - in_place: overwrite fpath with the fixed version. cannot be undone"""
    if not url and not root:
        raise ValueError("one of url or root is required")

    if not url:
        url = find_url(root, fpath, get_mime_for_name(fpath.name))
    with open(fpath, "r") as fh:
        if not in_place:
            return fix_links_in_html(url, fh.read())
        fixed = fix_links_in_html(url, fh.read())
    with open(fpath, "w") as fh:
        fh.write(fixed)


def fix_urls_in_css(
    url: str, content: str, folder: Optional[pathlib.Path] = None
) -> str:
    """CSS text with all url() fixed to namespace-aware ones (and fonts as data:)

    - url: target URL of this CSS in ZIM (no namespace)
    - content: CSS text to rewrite
    - folder: “parent” folder of CSS to find font files from"""

    def encapsulate(url):
        return f"url({url})"

    # split whole content on `url()` pattern to retrieve a list composed of
    # alternatively pre-pattern text and inside url() –– actual target text
    parts = re.split(r"url\((.+?)\)", content)
    for index, _ in enumerate(parts):
        if index % 2 == 0:  # skip even lines (0, 2, ..) as those are CSS code
            continue
        css_url = parts[index]  # css_urls are on odd lines

        # remove potential quotes (can be none, single or double)
        if css_url[0] and css_url[-1] == "'":
            css_url = css_url[1:-1]
        if css_url[0] and css_url[-1] == '"':
            css_url = css_url[1:-1]

        # don't rewrite data: and external urls
        if re.match(r"^(http:|https:|://|data:|#)", css_url):
            parts[index] = encapsulate(css_url)
            continue

        # parse as a URL to extract querystring and fragment
        _, _, target, query, fragment = urllib.parse.urlsplit(css_url)

        # fonts must be inserted inline using data: URL to prevent loading error
        # due to the Same Origin Security Policy with some readers/browsers.
        target_mime = get_mime_for_name(target)
        if target_mime in FONT_MIMES and folder is not None:
            fixed = get_base64_src_of(folder / target, target_mime)
        else:
            fixed = fix_target_for(
                pathlib.Path("."), pathlib.Path(url), pathlib.Path(target)
            )
            if query or fragment:
                fixed = urllib.parse.urlunsplit(("", "", fixed, query, fragment))

        parts[index] = encapsulate(fixed)
    return "".join(parts)


def fix_urls_in_css_file(
    fpath: pathlib.Path,
    url: Optional[str] = None,
    root: Optional[pathlib.Path] = None,
    in_place: Optional[bool] = False,
) -> Union[str, None]:
    """Fix CSS links from a file. Multiple behaviors

    - fpath: path to CSS file on disk
    - url: target URL of this CSS in ZIM (no namespace)
    - root: root folder of content (to guess url from)
    One of `url` or `root` is required
    - in_place: overwrite fpath with the fixed version. cannot be undone"""
    if not url and not root:
        raise ValueError("one of url or root is required")

    if not url:
        url = find_url(root, fpath, get_mime_for_name(fpath.name))
    with open(fpath, "r") as fh:
        if not in_place:
            return fix_urls_in_css(url, fh.read(), folder=fpath.parent)
        fixed = fix_urls_in_css(url, fh.read(), folder=fpath.parent)
    with open(fpath, "w") as fh:
        fh.write(fixed)
