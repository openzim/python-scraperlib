""" Tools to work with HTML contents """

import pathlib
from typing import BinaryIO, TextIO

from bs4 import BeautifulSoup, element

from zimscraperlib.types import ARTICLE_MIME


def find_title_in(content: str | BinaryIO | TextIO, mime_type: str | None) -> str:
    """Extracted title from HTML content

    blank on failure to extract and non-HTML files"""
    if mime_type != ARTICLE_MIME:
        return ""
    title_tag = BeautifulSoup(content, "lxml").find("title")
    return title_tag.text if title_tag else ""


def find_title_in_file(fpath: pathlib.Path, mime_type: str | None) -> str:
    """Extracted title from an HTML file"""
    try:
        with open(fpath) as fh:
            return find_title_in(fh, mime_type)
    except Exception:
        return ""


def find_language_in(content: str | BinaryIO | TextIO, mime_type: str) -> str:
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
                if not isinstance(node, element.Tag) or not node.has_attr(key):
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
    """Extracted language from an HTML file"""
    try:
        with open(fpath) as fh:
            return find_language_in(fh, mime_type)
    except Exception:
        return ""
