#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import sys
import shutil
import subprocess

import pytest
import libzim.reader

from zimscraperlib.zim import Blob
from zimscraperlib.zim.filesystem import FileArticle, FaviconArticle, make_zim_file


def test_filearticle(tmp_path, png_image):
    fpath = tmp_path / png_image.name
    shutil.copyfile(png_image, fpath)

    # ensure all properties of a FileArticle representing a binary are correct
    article = FileArticle(tmp_path, fpath, False)
    assert article.get_url() == "I/commons.png"
    assert article.get_title() == ""
    assert article.is_redirect() is False
    assert article.get_mime_type() == "image/png"
    assert article.get_filename() == ""
    assert article.should_compress() is False
    assert article.should_index() is False
    assert isinstance(article.get_data(), Blob)
    with pytest.raises(NotImplementedError):
        article.get_redirect_url()


def test_filearticle2(tmp_path, html_page):
    fpath = tmp_path / "test.html"
    with open(fpath, "w") as fh:
        fh.write(html_page)

    # ensure all properties of a FileArticle representing an article are correct
    article = FileArticle(tmp_path, fpath, True)
    assert article.get_url() == "A/test.html"
    assert article.get_title() == "Kiwix lets you access free knowledge – even offline"
    assert article.is_redirect() is False
    assert article.get_mime_type() == "text/html"
    assert article.get_filename() == ""
    assert article.should_compress() is True
    assert article.should_index() is True
    assert isinstance(article.get_data(), Blob)
    with pytest.raises(NotImplementedError):
        article.get_redirect_url()


def test_faviconarticle(tmp_path, png_image):
    # ensure FaviconArticle are proper redirect to the image article
    article = FaviconArticle(png_image.parent, png_image)
    assert article.get_url() == "-/favicon"
    assert article.get_title() == ""
    assert article.is_redirect() is True
    assert article.get_mime_type() == ""
    assert article.get_filename() == ""
    assert article.should_compress() is False
    assert article.should_index() is False
    assert article.get_data() == ""
    assert article.get_redirect_url() == f"I/{png_image.name}"


def test_make_zim_file_fail_nobuildir(build_data):
    # ensure we fail on missing build dir
    with pytest.raises(IOError):
        make_zim_file(**build_data)
    assert not build_data["fpath"].exists()


def test_make_zim_file_fail_nofavicon(build_data):
    # ensure we fail on missing favicon
    build_data["build_dir"].mkdir()
    with pytest.raises(IOError):
        make_zim_file(**build_data)
    assert not build_data["fpath"].exists()


def test_make_zim_file_working(build_data, png_image):
    build_data["build_dir"].mkdir()

    # add an image
    shutil.copyfile(png_image, build_data["build_dir"] / png_image.name)
    # add an HTML file
    with open(build_data["build_dir"] / "welcome", "w") as fh:
        fh.write("<html><title>Coucou</title></html>")
    # add a CSS file
    with open(build_data["build_dir"] / "style.css", "w") as fh:
        fh.write("body { background-color: red; }")
    # add a JS file
    with open(build_data["build_dir"] / "app.js", "w") as fh:
        fh.write("console.log(window);")

    make_zim_file(**build_data)
    assert build_data["fpath"].exists()
    with libzim.reader.File(build_data["fpath"]) as reader:
        # A/welcome (actual) and two redirs
        assert reader.get_namespace_count("A") == 3
        # I/commons.png (actual) and two redirs
        assert reader.get_namespace_count("I") == 3
        # 1 x CSS, 1x JS and -/favicon redirect
        assert reader.get_namespace_count("-") == 3

        assert reader.get_article("-/style.css").mimetype == "text/css"
        assert reader.get_article("-/app.js").mimetype == "application/javascript"
        assert reader.get_suggestions_results_count("bienvenue") == 2
        assert reader.get_suggestions_results_count("coucou") == 2
        assert "A/Accueil" in list(reader.suggest("bienvenue"))


def test_make_zim_file_exceptions_while_building(tmp_path, png_image, build_data):
    build_data["build_dir"].mkdir()
    shutil.copyfile(png_image, build_data["build_dir"] / png_image.name)
    build_data["redirects_file"] = tmp_path / "toto.tsv"
    with pytest.raises(FileNotFoundError):
        make_zim_file(**build_data, workaround_nocancel=False)
    # disabled workaround, we shall have a ZIM file
    assert build_data["fpath"].exists()


def test_make_zim_file_no_file_on_error(tmp_path, png_image, build_data):
    build_data["build_dir"].mkdir()
    shutil.copyfile(png_image, build_data["build_dir"] / png_image.name)
    build_data["redirects_file"] = tmp_path / "toto.tsv"
    pycode = f"""import sys
import pathlib
from zimscraperlib.zim.filesystem import make_zim_file
try:
    make_zim_file(
        build_dir=pathlib.Path("{build_data['build_dir']}"),
        fpath=pathlib.Path("{build_data['fpath']}"),
        name="test-zim",
        main_page="welcome",
        favicon="{png_image.name}",
        title="Test ZIM",
        description="A test ZIM",
        redirects_file="{build_data["redirects_file"]}")
except Exception as exc:
    print(exc)
finally:
    print("Program exiting")
"""

    py = subprocess.run([sys.executable, "-c", pycode])
    # returncode will be either 0 or -11, depending on garbage collection
    # in scrapers, we want to be able to fail on errors and absolutely don't want to
    # create a ZIM file, so SEGFAULT on exit it (somewhat) OK
    assert py.returncode in (0, 11, -6, -11)  # SIGSEV is 11
    assert not build_data["fpath"].exists()
