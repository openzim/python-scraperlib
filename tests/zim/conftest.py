#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import pytest


@pytest.fixture(scope="function")
def html_page():
    """ sample HTML content with title """
    return """
<!DOCTYPE html>
<html lang="en-US">
<head>
    <meta charset="UTF-8" />
<meta http-equiv="X-UA-Compatible" content="IE=edge">
    <link rel="pingback" href="" />
    <title>Kiwix lets you access free knowledge – even offline</title>
    <meta name="description" content="Internet content for people without internet access. On computers, phone or raspberry hotspots: Wikipedia or any website, offline, anytime, for free!" />
</head>
<body>
</html>
"""


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
def css_str():
    """ CSS content with variants of url() pointing to images """
    return """
.urls {
    background-image: url(https://example.com/images/myImg.jpg);
    background-image: url(http://example.com/images/myImg.jpg);
    background-image: url(http://example.com/images/myImg.jpg?v=21);
    background-image: url(http://example.com/images/myImg.jpg?v=21&x=y);
    background-image: url('http://example.com/images/myImg.jpg');
    background-image: url('http://example.com/images/myImg.jpg?v=21&x=y');
    background-image: url("http://example.com/images/myImg.jpg");
    background-image: url("http://example.com/images/myImg.jpg?v=21&x=y");
}
.imgs {
    background-image: url(sample.jpg);
    background-image: url(sample.jpg?v=21&x=y);
    background-image: url('sample.jpg');
    background-image: url('sample.jpg?v=21&x=y');
    background-image: url("sample.jpg");
    background-image: url("sample.jpg?v=21&x=y");
    background-image: url(sample.jpg#toto);
    background-image: url(sample.jpg?yolo#toto);
    background-image: url('sample.jpg#toto');
    background-image: url('sample.jpg?yolo#toto');
    background-image: url("sample.jpg#toto");
    background-image: url("sample.jpg?yolo#toto");
}
.imgs {
    background-image: url(assets/images/sample.jpg);
    background-image: url(assets/images/sample.jpg?v=21&x=y);
    background-image: url('assets/images/sample.jpg');
    background-image: url('assets/images/sample.jpg?v=21&x=y');
    background-image: url("assets/images/sample.jpg");
    background-image: url("assets/images/sample.jpg?v=21&x=y");
    background-image: url(assets/images/sample.jpg#toto);
    background-image: url(assets/images/sample.jpg?yolo#toto);
    background-image: url('assets/images/sample.jpg#toto');
    background-image: url('assets/images/sample.jpg?yolo#toto');
    background-image: url("assets/images/sample.jpg#toto");
    background-image: url("assets/images/sample.jpg?yolo#toto");
}
.specials {
    background-image: url(data:image/png;base64,iVBORw0);
    background-image: url(#IDofSVGpath);
}"""


@pytest.fixture(scope="function")
def css_str_down():
    return ".down { background-image: url(../sample.jpg); }"


@pytest.fixture(scope="function")
def css_str_with_fonts():
    """ CSS content with url() pointing to fonts """
    return """
.fonts {
    background-image: url(font/DroidSans.ttf);
    background-image: url(font/DroidSans.ttf?v=21&x=y);
    background-image: url('font/DroidSans.ttf');
    background-image: url('font/DroidSans.ttf?v=21&x=y');
    background-image: url("font/DroidSans.ttf");
    background-image: url("font/DroidSans.ttf?v=21&x=y");
    background-image: url(font/DroidSans.ttf#toto);
    background-image: url(font/DroidSans.ttf?yolo#toto);
    background-image: url('font/DroidSans.ttf#toto');
    background-image: url('font/DroidSans.ttf?yolo#toto');
    background-image: url("font/DroidSans.ttf#toto");
    background-image: url("font/DroidSans.ttf?yolo#toto");
}
"""


@pytest.fixture(scope="function")
def css_file(tmp_path, css_str):
    fpath = tmp_path / "test.css"
    with open(fpath, "w") as fh:
        fh.write(css_str)
    return fpath


@pytest.fixture(scope="function")
def build_data(tmp_path, png_image):
    fpath = tmp_path / "test.zim"
    redirects_file = tmp_path / "redirects.tsv"
    with open(redirects_file, "w") as fh:
        fh.write("A\tAccueil\tBienvenue !!\tA/welcome\n")
        fh.write("I\tAccueil\t\tI/commons.png\n")
        fh.write("A\timage\t\tI/commons.png\n")
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
        "redirects": [("I/picture", "I/commons.png", "")],
        "redirects_file": redirects_file,
    }
