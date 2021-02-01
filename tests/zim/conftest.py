#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import pytest


@pytest.fixture(scope="function")
def html_str():
    """ sample HTML content with various links """
    return """<html>
<body>
<ul>
    <li><a href="download/toto.pdf">PDF doc</a></li>
    <li><a href="download/toto.txt">text file</a></li>
    <li><a href="dest.html">HTML link</a></li>
    <li><a href="no-extension">no ext link</a></li>
    <li><a href="http://www.example.com/index/sample.html">external link</a></li>
    <li><a href="mailto:example@example.com">e-mail link</a></li>
    <li><a media="">no href link</a></li>
<object data="download/toto.jpg" width="300" height="200"></object>
<script src="assets/js/bootstrap/bootsrap.css?v=20190101"></script>
</body>
</html>
"""


@pytest.fixture(scope="function")
def html_file(tmp_path, html_str):
    fpath = tmp_path / "test.html"
    with open(fpath, "w") as fh:
        fh.write(html_str)
    return fpath


@pytest.fixture(scope="function")
def build_data(tmp_path, png_image):
    fpath = tmp_path / "test.zim"
    redirects_file = tmp_path / "redirects.tsv"
    with open(redirects_file, "w") as fh:
        fh.write(" \tAccueil\tBienvenue !!\twelcome\n")
        fh.write(" \tAccueil\t\tcommons.png\n")
        fh.write(" \timage\t\tcommons.png\n")
    build_dir = tmp_path / "build"
    return {
        "build_dir": build_dir,
        "fpath": fpath,
        "name": "test-zim",
        "main_page": "welcome",
        "favicon": png_image.name,
        "title": "Test ZIM",
        "description": "A test ZIM",
        "date": None,
        "language": "fra",
        "creator": "test",
        "publisher": "test",
        "tags": ["test"],
        "redirects": [("picture", "commons.png", "")],
        "redirects_file": redirects_file,
    }
