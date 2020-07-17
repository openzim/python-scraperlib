#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import re

import pytest
import libzim.reader

from zimscraperlib.constants import UTF8
from zimscraperlib.zim.creator import Creator, StaticArticle, Compression


def count_links(article, pattern):
    """ number of occurences of a pattern inside an article """
    content = bytes(article.content).decode(UTF8)
    return len(re.findall(pattern, content))


def test_zim_creator(tmp_path, png_image, css_file, html_file, css_str, html_str):
    fpath = tmp_path / "test.zim"
    main_page, language, title = "welcome", "fra", "My Title"
    tags = ";".join(["toto", "tata"])
    redir_url = "A/ola"

    with Creator(fpath, main_page, language, title=title, tags=tags) as creator:
        # rewritten CSS from string
        creator.add_css("test.css", content=css_str, rewrite_links=True)
        # verbatim CSS from string
        creator.add_css("test2.css", content=css_str, rewrite_links=False)
        # rewritten CSS from file
        creator.add_css("test3.css", fpath=css_file, rewrite_links=True)
        # verbatim CSS from file
        creator.add_css("test4.css", fpath=css_file, rewrite_links=False)
        # rewritten HTML from string
        creator.add_article("welcome", "Welcome", content=html_str, rewrite_links=True)
        # verbatim HTML from string
        creator.add_article("welcome2", "wel2", content=html_str, rewrite_links=False)
        # rewritten HTML from file
        creator.add_article("welcome3", "Wel3", fpath=html_file, rewrite_links=True)
        # verbatim HTML from file
        creator.add_article("welcome4", "wel4", fpath=html_file, rewrite_links=False)
        # single binary image
        creator.add_binary("images/yahoo.png", fpath=png_image)
        # redirect to our main page (no title)
        creator.add_redirect("A/home", "A/welcome")
        # redirect to our main page (with a custom title)
        creator.add_redirect("A/home2", "A/welcome", "Home !!")

        # redirect using StaticArticle
        creator.add_zim_article(StaticArticle(url=redir_url, redirect_url="A/welcome"))

        # ensure args requirement are checked
        with pytest.raises(ValueError, match="One of fpath or content is required"):
            creator.add_binary("images/yahoo.png")
        with pytest.raises(ValueError, match="One of fpath or content is required"):
            # private method
            creator._add_rewriten(
                "-", "test3.css", "", "text/css", False, False, False, None
            )

    assert fpath.exists()

    with libzim.reader.File(fpath) as reader:
        assert reader.get_metadata("Title").decode(UTF8) == title
        assert reader.get_metadata("Language").decode(UTF8) == language
        assert reader.get_metadata("Tags").decode(UTF8) == tags
        assert reader.main_page_url == f"A/{main_page}"
        # make sure we have our image
        assert reader.get_article("I/images/yahoo.png")
        # make sure we have our redirects
        assert reader.get_article(redir_url).is_redirect
        assert (
            reader.get_article(redir_url).get_redirect_article().longurl
            == f"A/{main_page}"
        )
        # make sure we have full text and title indexes
        assert reader.get_article("X/title/xapian")
        assert reader.get_article("X/fulltext/xapian")
        # make sure titles were indexed
        assert "A/home2" in list(reader.suggest("Home !!"))
        # make sure full text was indexed
        assert reader.get_search_results_count("PDF doc") >= 1

        # ensure CSS rewriting is OK
        assert count_links(reader.get_article("-/test.css"), r"../I") == 24
        assert count_links(reader.get_article("-/test3.css"), r"../I") == 24

        # ensure non-rewritten articles have not been rewritten
        assert count_links(reader.get_article("-/test2.css"), r"../I") == 0
        assert count_links(reader.get_article("-/test4.css"), r"../I") == 0
        assert bytes(reader.get_article("-/test2.css").content).decode(UTF8) == css_str
        assert bytes(reader.get_article("-/test4.css").content).decode(UTF8) == css_str

        # ensure CSS rewriting is OK
        assert count_links(reader.get_article("A/welcome"), r"../A") == 2
        assert count_links(reader.get_article("A/welcome"), r"../-") == 2
        assert count_links(reader.get_article("A/welcome"), r"dest.html") == 1
        assert count_links(reader.get_article("A/welcome3"), r"../I") == 1
        assert count_links(reader.get_article("A/welcome3"), r"../-") == 2
        assert count_links(reader.get_article("A/welcome3"), r"../A") == 2
        assert count_links(reader.get_article("A/welcome3"), r"dest.html") == 1

        # ensure non-rewritten articles have not been rewritten
        assert count_links(reader.get_article("A/welcome2"), r"../I") == 0
        assert count_links(reader.get_article("A/welcome4"), r"../I") == 0
        assert bytes(reader.get_article("A/welcome2").content).decode(UTF8) == html_str
        assert bytes(reader.get_article("A/welcome4").content).decode(UTF8) == html_str


def test_create_without_workaround(tmp_path):
    fpath = tmp_path / "test.zim"

    with Creator(
        fpath, "welcome", "fra", title="My Title", workaround_nocancel=False
    ) as creator:
        print("creator", creator, creator.workaround_nocancel)
        with pytest.raises(RuntimeError, match="AttributeError"):
            creator.add_zim_article("hello")


def test_noindexlanguage(tmp_path):
    fpath = tmp_path / "test.zim"
    with Creator(fpath, "welcome", "", "My Title") as creator:
        creator.add_zim_article(StaticArticle(url="A/welcome", content="hello"))
        creator.update_metadata(language="bam")

    with libzim.reader.File(fpath) as reader:
        assert reader.get_metadata("Language").decode(UTF8) == "bam"
        assert reader.get_article("X/title/xapian")
        with pytest.raises(KeyError):
            reader.get_article("X/fulltext/xapian")


def test_double_close(tmp_path):
    fpath = tmp_path / "test.zim"
    with Creator(fpath, "welcome", "fra", "My Title") as creator:
        creator.add_zim_article(StaticArticle(url="A/welcome", content="hello"))

    # ensure we can close an already closed creator
    creator.close()


@pytest.mark.parametrize(
    "compression", list(Compression.__members__) + [None],
)
def test_compression(tmp_path, html_str, compression):
    with Creator(
        tmp_path / "test.zim", "welcome", "", "My Title", compression=compression
    ) as creator:
        creator.add_article("welcome", "Welcome", content=html_str, rewrite_links=True)


@pytest.mark.parametrize(
    "min_chunk_size", [512, 1024, 2048, 4096, None],
)
def test_min_chunk_size(tmp_path, html_str, min_chunk_size):
    with Creator(
        tmp_path / "test.zim", "welcome", "", "", min_chunk_size=min_chunk_size
    ) as creator:
        creator.add_article("welcome", "Welcome", content=html_str, rewrite_links=True)
