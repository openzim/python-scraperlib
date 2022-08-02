#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import io
import os
import pathlib
import random
import shutil
import subprocess
import sys
import tempfile
import time

import pytest
from libzim.writer import Compression

from zimscraperlib.constants import UTF8
from zimscraperlib.download import save_large_file, stream_file
from zimscraperlib.filesystem import delete_callback
from zimscraperlib.zim import Archive, Creator, StaticItem, URLItem
from zimscraperlib.zim.providers import FileLikeProvider, URLProvider


class SpecialURLProvider(URLProvider):
    """prevents crash on invalid size"""

    def get_size(self) -> int:
        return self.size or 0


class SpecialURLProviderItem(StaticItem):
    def get_contentprovider(self):
        return SpecialURLProvider(self.url)


class FileLikeProviderItem(StaticItem):
    def get_contentprovider(self):
        return FileLikeProvider(self.fileobj)


def test_zim_creator(tmp_path, png_image, html_file, html_str):
    fpath = tmp_path / "test.zim"
    main_path, language, title = "welcome", "fra", "My Title"
    tags = ";".join(["toto", "tata"])

    with open(png_image, "rb") as fh:
        png_data = fh.read()

    with Creator(fpath, main_path, language, title=title, tags=tags) as creator:
        # verbatim HTML from string
        creator.add_item_for("welcome", "wel", content=html_str, is_front=True)
        # verbatim HTML from file
        creator.add_item_for("welcome3", "wel3", fpath=html_file)
        creator.add_item_for("welcome4", "wel4", fpath=html_file)
        # single binary image
        creator.add_item_for(
            "images/yahoo.png", "Home !!", fpath=png_image, is_front=True
        )
        # redirect to our main page (no title)
        creator.add_redirect("home", "welcome")
        # redirect to our main page (with a custom title)
        creator.add_redirect("home2", "welcome", "Home !!")
        creator.add_redirect("home3", "welcome3", "Home !!", is_front=True)
        creator.add_redirect("home4", "welcome4", "Home !!", is_front=False)

        # ensure args requirement are checked
        with pytest.raises(ValueError, match="One of fpath or content is required"):
            creator.add_item_for("images/yahoo.png")

        with open(png_image, "rb") as fh:
            creator.add_default_illustration(png_data)

    assert fpath.exists()

    reader = Archive(fpath)
    assert reader.get_metadata("Title").decode(UTF8) == title
    assert reader.get_metadata("Language").decode(UTF8) == language
    assert reader.get_metadata("Tags").decode(UTF8) == tags
    assert reader.main_entry.get_item().path == f"{main_path}"
    # make sure we have our image
    assert reader.get_item("images/yahoo.png")
    # make sure we have our redirects
    assert reader.get_entry_by_path("home2").is_redirect
    assert reader.get_entry_by_path("home2").get_redirect_entry().path == f"{main_path}"
    # make sure titles were indexed (html with title for xapian ; redirects are not)
    # see https://github.com/openzim/python-libzim/issues/125
    # see https://github.com/openzim/libzim/issues/642
    assert "home2" not in list(reader.get_suggestions("Home !!"))  # no is_front > False
    assert "home3" in list(reader.get_suggestions("Home !!"))  # is_front=True
    assert "home4" not in list(reader.get_suggestions("Home !!"))  # is_front=False
    assert "images/yahoo.png" in list(reader.get_suggestions("Home !!"))  # is_frontTrue
    # make sure full text was indexed
    assert reader.get_search_results_count("PDF doc") >= 1

    # ensure non-rewritten articles have not been rewritten
    assert bytes(reader.get_item("welcome").content).decode(UTF8) == html_str
    assert bytes(reader.get_item("welcome3").content).decode(UTF8) == html_str

    # ensure illustration is present and corrext
    assert reader.has_illustration()
    assert bytes(reader.get_illustration_item().content) == png_data


def test_create_without_workaround(tmp_path):
    fpath = tmp_path / "test.zim"

    with Creator(
        fpath, "welcome", "fra", title="My Title", workaround_nocancel=False
    ) as creator:
        with pytest.raises(RuntimeError, match="AttributeError"):
            creator.add_item("hello")


def test_noindexlanguage(tmp_path):
    fpath = tmp_path / "test.zim"
    with Creator(fpath, "welcome", "") as creator:
        creator.add_item(StaticItem(path="welcome", content="hello"))
        creator.update_metadata(language="bam")
        creator.add_item_for("index", "Index", content="-", mimetype="text/html")

    reader = Archive(fpath)
    assert reader.get_metadata("Language").decode(UTF8) == "bam"
    # html content triggers both title and content xapian indexes
    # but since indexing is disabled, we should only have title one
    assert reader.has_title_index
    assert not reader.has_fulltext_index


def test_add_item_for(tmp_path):
    fpath = tmp_path / "test.zim"
    # test without mimetype
    with Creator(fpath, "welcome", "") as creator:
        creator.add_item_for(path="welcome", title="hello", content="hello")

    # test missing fpath and content
    with Creator(fpath, "welcome", "") as creator:
        with pytest.raises(ValueError):
            creator.add_item_for(path="welcome", title="hello")


def test_add_item_for_delete(tmp_path, html_file):
    fpath = tmp_path / "test.zim"
    local_path = pathlib.Path(tmp_path / "somefile.html")

    # copy file to local path
    shutil.copyfile(html_file, local_path)

    with Creator(fpath, "welcome", "") as creator:
        creator.add_item_for(fpath=local_path, path="index", delete_fpath=True)

    assert not local_path.exists()

    reader = Archive(fpath)
    assert reader.get_item("index")


def test_add_item_for_delete_fail(tmp_path, png_image):
    fpath = tmp_path / "test.zim"
    local_path = pathlib.Path(tmp_path / "somefile.png")

    # copy file to local path
    shutil.copyfile(png_image, local_path)

    def remove_source(item):
        print("##########", "remove_source")
        os.remove(item.filepath)

    with Creator(fpath, "welcome", "") as creator:
        creator.add_item(
            StaticItem(filepath=local_path, path="index", callback=remove_source),
            callback=(delete_callback, local_path),
        )
    assert not local_path.exists()

    reader = Archive(fpath)
    assert reader.get_item("index")


def test_compression(tmp_path):
    fpath = tmp_path / "test.zim"
    with Creator(tmp_path / "test.zim", "welcome", "", compression="lzma") as creator:
        creator.add_item(StaticItem(path="welcome", content="hello"))

    with Creator(fpath, "welcome", "", compression=Compression.lzma) as creator:
        creator.add_item(StaticItem(path="welcome", content="hello"))


def test_double_finish(tmp_path):
    fpath = tmp_path / "test.zim"
    with Creator(fpath, "welcome", "fra") as creator:
        creator.add_item(StaticItem(path="welcome", content="hello"))

    # ensure we can finish an already finished creator
    creator.finish()


def test_cannot_finish(tmp_path):
    creator = Creator(tmp_path / "test.zim")
    creator.can_finish = False
    creator.finish()


def test_sourcefile_removal(tmp_path, html_file):

    fpath = tmp_path / "test.zim"
    with Creator(fpath) as creator:
        # using a temp dir so file still have a meaningful name
        tmpdir = tempfile.TemporaryDirectory(dir=tmp_path)  # can't use contextmgr
        # copy html to folder
        src_path = pathlib.Path(tmpdir.name, "source.html")
        shutil.copyfile(html_file, src_path)
        creator.add_item(StaticItem(filepath=src_path, path=src_path.name, ref=tmpdir))
        del tmpdir

    assert not src_path.exists()


def test_sourcefile_removal_std(tmp_path, html_file):

    fpath = tmp_path / "test.zim"
    paths = []
    with Creator(fpath) as creator:
        for idx in range(0, 4):
            # copy html to folder
            paths.append(pathlib.Path(tmp_path / f"source{idx}.html"))
            shutil.copyfile(html_file, paths[-1])
            creator.add_item(
                StaticItem(
                    filepath=paths[-1],
                    path=paths[-1].name,
                    mimetype="text/html",
                ),
                callback=(delete_callback, paths[-1]),
            )
    for path in paths:
        assert not path.exists()


def test_sourcefile_noremoval(tmp_path, html_file):
    # copy html to folder
    src_path = tmp_path / "source.html"
    shutil.copyfile(html_file, src_path)

    fpath = tmp_path / "test.zim"
    with Creator(fpath) as creator:
        creator.add_item(StaticItem(path=src_path.name, filepath=src_path))

    assert src_path.exists()


def test_urlitem_badurl(tmp_path):

    with Creator(tmp_path / "test.zim") as creator:
        with pytest.raises(IOError, match="Unable to access URL"):
            creator.add_item(URLItem(url="httpo://hello:helloe:hello/"))


def test_urlitem_html(tmp_path, gzip_html_url):
    file_path = tmp_path / "file.html"
    save_large_file(gzip_html_url, file_path)
    with open(file_path, "rb") as fh:
        file_bytes = fh.read()

    fpath = tmp_path / "test.zim"
    with Creator(fpath) as creator:
        creator.add_item(URLItem(url=gzip_html_url))

    zim = Archive(fpath)
    assert bytes(zim.get_item("wiki/Main_Page").content) == file_bytes


def test_urlitem_nonhtmlgzip(tmp_path, gzip_nonhtml_url):
    file_path = tmp_path / "file.txt"
    save_large_file(gzip_nonhtml_url, file_path)
    with open(file_path, "rb") as fh:
        file_bytes = fh.read()

    fpath = tmp_path / "test.zim"
    with Creator(fpath) as creator:
        creator.add_item(URLItem(url=gzip_nonhtml_url))

    with Creator(fpath) as creator:
        creator.add_item(URLItem(url=gzip_nonhtml_url, use_disk=True))

    zim = Archive(fpath)
    assert bytes(zim.get_item("robots.txt").content) == file_bytes


def test_urlitem_binary(tmp_path, png_image_url):
    file_path = tmp_path / "file.png"
    save_large_file(png_image_url, file_path)
    with open(file_path, "rb") as fh:
        file_bytes = fh.read()

    fpath = tmp_path / "test.zim"
    with Creator(fpath) as creator:
        creator.add_item(URLItem(url=png_image_url))

    zim = Archive(fpath)
    assert (
        bytes(zim.get_item("static/images/project-logos/commonswiki.png").content)
        == file_bytes
    )


def test_urlitem_staticcontent(tmp_path, gzip_nonhtml_url):
    fpath = tmp_path / "test.zim"
    with Creator(fpath) as creator:
        creator.add_item(URLItem(url=gzip_nonhtml_url, content="hello"))

    zim = Archive(fpath)
    assert bytes(zim.get_item("robots.txt").content) == b"hello"


def test_filelikeprovider_nosize(tmp_path, png_image_url):
    fileobj = io.BytesIO()
    stream_file(png_image_url, byte_stream=fileobj)

    fpath = tmp_path / "test.zim"
    with Creator(fpath) as creator:
        creator.add_item(FileLikeProviderItem(fileobj=fileobj, path="one.png"))

    zim = Archive(fpath)
    assert bytes(zim.get_item("one.png").content) == fileobj.getvalue()


def test_urlprovider(tmp_path, png_image_url):
    file_path = tmp_path / "file.png"
    save_large_file(png_image_url, file_path)
    with open(file_path, "rb") as fh:
        file_bytes = fh.read()

    fpath = tmp_path / "test.zim"
    with Creator(fpath) as creator:
        creator.add_item(SpecialURLProviderItem(url=png_image_url, path="one.png"))

    zim = Archive(fpath)
    assert bytes(zim.get_item("one.png").content) == file_bytes


def test_urlprovider_nolength(tmp_path, png_image_url, png_image):

    # save url's content locally using external tool
    png_image = tmp_path / "original.png"
    save_large_file(png_image_url, png_image)
    with open(png_image, "rb") as fh:
        png_image_bytes = fh.read()

    # create and start an http server without Content-Length support
    server_fpath = tmp_path / "httpd.py"
    port = random.randint(10000, 20000)
    server_code = """
from http.server import BaseHTTPRequestHandler, HTTPServer

class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "image/png")
        if "gzip" in self.path:
            self.send_header("Content-Encoding", "gzip")
        self.end_headers()
        with open("{src}", "rb") as fh:
            self.wfile.write(fh.read())


with HTTPServer(('', {port}), handler) as server:
    server.serve_forever()

"""
    with open(server_fpath, "w") as fh:
        fh.write(
            server_code.replace("{port}", str(port)).replace("{src}", str(png_image))
        )

    httpd = subprocess.Popen([sys.executable, server_fpath])
    time.sleep(2)  # allow http server to start

    fpath = tmp_path / "test.zim"
    try:
        with tempfile.TemporaryDirectory() as tmp_dir, Creator(fpath) as creator:
            tmp_dir = pathlib.Path(tmp_dir)
            creator.add_item(
                URLItem(
                    url=f"http://localhost:{port}/hoho.png",
                    path="B",
                    tmp_dir=tmp_dir,
                    use_disk=True,
                )
            )
            creator.add_item(
                URLItem(url=f"http://localhost:{port}/home.png", tmp_dir=tmp_dir)
            )

            creator.add_item(
                SpecialURLProviderItem(
                    url=f"http://localhost:{port}/home.png", mimetype="image/png"
                )
            )
    finally:
        httpd.terminate()

    zim = Archive(fpath)
    assert bytes(zim.get_item("home.png").content) == png_image_bytes
    assert bytes(zim.get_item("B").content) == png_image_bytes


def test_item_callback(tmp_path, html_file):
    fpath = tmp_path / "test.zim"

    class Store:
        called = False

    def cb():
        Store.called = True

    with Creator(fpath) as creator:
        creator.add_item(
            StaticItem(path=html_file.name, filepath=html_file), callback=cb
        )

    assert Store.called is True


def test_compess_hints(tmp_path, html_file):
    with Creator(tmp_path / "test.zim") as creator:
        creator.add_item_for(
            path=html_file.name,
            fpath=html_file,
            delete_fpath=True,
            should_compress=True,
        )


def test_callback_and_remove(tmp_path, html_file):
    class Store:
        called = 0

    def cb(*args):
        Store.called += 1

    # duplicate test file as we'll want to remove twice
    html_file2 = html_file.with_suffix(f".2{html_file.suffix}")
    shutil.copyfile(html_file, html_file2)

    with Creator(tmp_path / "test.zim") as creator:
        creator.add_item_for(
            path=html_file.name, fpath=html_file, delete_fpath=True, callback=cb
        )
        creator.add_item_for(
            path=html_file2.name,
            fpath=html_file2,
            delete_fpath=True,
            callback=(cb, html_file.name),
        )

    assert not html_file.exists()
    assert Store.called
    assert Store.called == 2


def test_duplicates(tmp_path):
    with Creator(tmp_path / "test.zim") as creator:
        creator.add_item_for(path="A", content="A")
        creator.add_item_for(path="C", content="C")
        creator.add_redirect(path="B", target_path="A")
        with pytest.raises(RuntimeError, match="existing dirent's title"):
            creator.add_item_for(path="A", content="test2")
        with pytest.raises(RuntimeError, match="existing dirent's title"):
            creator.add_redirect(path="B", target_path="C")


def test_ignore_duplicates(tmp_path):
    with Creator(tmp_path / "test.zim", ignore_duplicates=True) as creator:
        creator.add_item_for(path="A", content="A")
        creator.add_item_for(path="A", content="A2")
        creator.add_redirect(path="B", target_path="A")
        creator.add_redirect(path="B", target_path="C")
