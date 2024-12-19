import datetime
import io
import logging
import pathlib
import random
import shutil
import subprocess
import sys
import tempfile
import time
from types import NoneType
from typing import Any, NamedTuple
from unittest.mock import call, patch

import pytest
from libzim.writer import Compression  # pyright: ignore[reportMissingModuleSource]

from zimscraperlib.constants import UTF8
from zimscraperlib.download import save_large_file, stream_file
from zimscraperlib.filesystem import delete_callback
from zimscraperlib.typing import Callback
from zimscraperlib.zim import Archive, Creator, StaticItem, URLItem
from zimscraperlib.zim.metadata import (
    DEFAULT_DEV_ZIM_METADATA,
    AnyMetadata,
    CreatorMetadata,
    CustomMetadata,
    CustomTextMetadata,
    DateMetadata,
    DefaultIllustrationMetadata,
    DescriptionMetadata,
    FlavourMetadata,
    LanguageMetadata,
    LicenseMetadata,
    LongDescriptionMetadata,
    Metadata,
    NameMetadata,
    PublisherMetadata,
    ScraperMetadata,
    SourceMetadata,
    StandardMetadataList,
    TagsMetadata,
    TitleMetadata,
)
from zimscraperlib.zim.providers import FileLikeProvider, URLProvider


class SpecialURLProvider(URLProvider):
    """prevents crash on invalid size"""

    def get_size(self) -> int:
        return self.size or 0


class SpecialURLProviderItem(StaticItem):
    url: str

    def get_contentprovider(self):
        return SpecialURLProvider(self.url)


class FileLikeProviderItem(StaticItem):
    fileobj: io.BytesIO

    def get_contentprovider(self):
        if not self.fileobj:
            raise AttributeError("fileobj cannot be None")
        return FileLikeProvider(self.fileobj)


def test_zim_creator(
    tmp_path: pathlib.Path,
    png_image: pathlib.Path,
    html_file: pathlib.Path,
    html_str: str,
    html_str_cn: str,
):
    fpath = tmp_path / "test.zim"
    main_path = "welcome"
    tags = ";".join(["toto", "tata"])
    with open(png_image, "rb") as fh:
        png_data = fh.read()
    with Creator(fpath, main_path).config_dev_metadata(
        [TagsMetadata(tags), DefaultIllustrationMetadata(png_data)]
    ) as creator:
        # verbatim HTML from string
        creator.add_item_for("welcome", "wel", content=html_str, is_front=True)
        # verbatim HTML from bytes
        creator.add_item_for(
            "welcome1", "wel1", content=html_str.encode(), is_front=True
        )
        creator.add_item_for(
            "welcome2", "wel2", content=html_str_cn.encode("gb2312"), is_front=True
        )
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

    assert fpath.exists()

    reader = Archive(fpath)
    assert reader.get_text_metadata(
        "Title"
    ) == DEFAULT_DEV_ZIM_METADATA.Title.libzim_value.decode("UTF-8")
    assert reader.get_text_metadata(
        "Language"
    ) == DEFAULT_DEV_ZIM_METADATA.Language.libzim_value.decode("UTF-8")
    assert reader.get_text_metadata("Tags") == tags
    assert reader.main_entry.get_item().path == f"{main_path}"
    # make sure we have our image
    assert reader.get_item("images/yahoo.png")
    # make sure we have our redirects
    assert reader.get_entry_by_path("home2").is_redirect
    assert reader.get_entry_by_path("home2").get_redirect_entry().path == f"{main_path}"
    # make sure titles were indexed (html with title for xapian ; redirects are not)
    # see https://github.com/openzim/python-libzim/issues/125
    # see https://github.com/openzim/libzim/issues/642
    assert "home2" not in list(reader.get_suggestions("Home"))  # no is_front > False
    # assert "home3" in list(reader.get_suggestions("Home"))  # is_front=True
    assert "home4" not in list(reader.get_suggestions("Home"))  # is_front=False
    assert "images/yahoo.png" in list(reader.get_suggestions("Home"))  # is_frontTrue
    # make sure full text was indexed
    assert reader.get_search_results_count("PDF doc") >= 1

    # ensure non-rewritten articles have not been rewritten
    assert bytes(reader.get_item("welcome").content).decode(UTF8) == html_str
    assert bytes(reader.get_item("welcome1").content).decode(UTF8) == html_str
    assert bytes(reader.get_item("welcome2").content).decode("gb2312") == html_str_cn
    assert bytes(reader.get_item("welcome3").content).decode(UTF8) == html_str

    # ensure illustration is present and corrext
    assert reader.has_illustration()
    assert bytes(reader.get_illustration_item().content) == png_data


def test_create_without_workaround(tmp_path: pathlib.Path):
    fpath = tmp_path / "test.zim"

    with Creator(fpath, "welcome", workaround_nocancel=False).config_dev_metadata():
        with pytest.raises(RuntimeError):
            raise RuntimeError("erroring")
    assert fpath.exists()


def test_noindexlanguage(tmp_path: pathlib.Path):
    fpath = tmp_path / "test.zim"
    creator = Creator(fpath, "welcome").config_dev_metadata(LanguageMetadata("bam"))
    creator.config_indexing(False)
    with creator as creator:
        creator.add_item(StaticItem(path="welcome", content="hello"))
        creator.add_item_for("index", "Index", content="-", mimetype="text/html")

    reader = Archive(fpath)
    assert reader.get_text_metadata("Language") == "bam"
    # html content triggers both title and content xapian indexes
    # but since indexing is disabled, we should only have title one
    assert reader.has_title_index
    assert not reader.has_fulltext_index


def test_add_item_for(tmp_path: pathlib.Path):
    fpath = tmp_path / "test.zim"
    # test without mimetype
    with Creator(fpath, "welcome").config_dev_metadata() as creator:
        creator.add_item_for(path="welcome", title="hello", content="hello")

    # test missing fpath and content
    with Creator(fpath, "welcome").config_dev_metadata() as creator:
        with pytest.raises(ValueError):
            creator.add_item_for(path="welcome", title="hello")


def test_additem_bad_content(tmp_path: pathlib.Path):
    with Creator(tmp_path / "test.zim", "welcome").config_dev_metadata() as creator:
        with pytest.raises(RuntimeError, match="Unexpected type for content"):
            si = StaticItem(path="welcome", content="hello")
            si.content = 1  # pyright: ignore[reportAttributeAccessIssue]
            creator.add_item(si)


def test_add_item_for_delete(tmp_path: pathlib.Path, html_file: pathlib.Path):
    fpath = tmp_path / "test.zim"
    local_path = pathlib.Path(tmp_path / "somefile.html")

    # copy file to local path
    shutil.copyfile(html_file, local_path)

    with Creator(fpath, "welcome").config_dev_metadata() as creator:
        creator.add_item_for(fpath=local_path, path="index", delete_fpath=True)

    assert not local_path.exists()

    reader = Archive(fpath)
    assert reader.get_item("index")


def test_add_item_for_delete_fail(tmp_path: pathlib.Path, png_image: pathlib.Path):
    fpath = tmp_path / "test.zim"
    local_path = pathlib.Path(tmp_path / "somefile.png")

    # copy file to local path
    shutil.copyfile(png_image, local_path)

    with Creator(fpath, "welcome").config_dev_metadata() as creator:
        creator.add_item(
            StaticItem(
                filepath=local_path,
                path="index",
            ),
            callbacks=Callback(func=delete_callback, kwargs={"fpath": local_path}),
        )
    assert not local_path.exists()

    reader = Archive(fpath)
    assert reader.get_item("index")


def test_add_item_empty_content(tmp_path: pathlib.Path):
    fpath = tmp_path / "test.zim"
    # test with incorrect content type
    with Creator(fpath, "welcome").config_dev_metadata() as creator:
        creator.add_item_for(
            path="welcome",
            title="hello",
            content="",
        )


def test_compression(tmp_path: pathlib.Path):
    fpath = tmp_path / "test.zim"
    with Creator(
        tmp_path / "test.zim", "welcome", compression="zstd"
    ).config_dev_metadata() as creator:
        creator.add_item(StaticItem(path="welcome", content="hello"))

    with Creator(
        fpath, "welcome", compression=Compression.zstd.name
    ).config_dev_metadata() as creator:
        creator.add_item(StaticItem(path="welcome", content="hello"))


def test_double_finish(tmp_path: pathlib.Path):
    fpath = tmp_path / "test.zim"
    with Creator(fpath, "welcome").config_dev_metadata() as creator:
        creator.add_item(StaticItem(path="welcome", content="hello"))

    # ensure we can finish an already finished creator
    creator.finish()


def test_cannot_finish(tmp_path: pathlib.Path):
    creator = Creator(tmp_path / "test.zim", "")
    creator.can_finish = False
    creator.finish()


def test_sourcefile_removal(tmp_path: pathlib.Path, html_file: pathlib.Path):
    fpath = tmp_path / "test.zim"
    with Creator(fpath, "").config_dev_metadata() as creator:
        # using a temp dir so file still have a meaningful name
        tmpdir = tempfile.TemporaryDirectory(dir=tmp_path)  # can't use contextmgr
        # copy html to folder
        src_path = pathlib.Path(tmpdir.name, "source.html")
        shutil.copyfile(html_file, src_path)
        creator.add_item(StaticItem(filepath=src_path, path=src_path.name, ref=tmpdir))
        del tmpdir

    assert not src_path.exists()


def test_sourcefile_removal_std(tmp_path: pathlib.Path, html_file: pathlib.Path):
    fpath = tmp_path / "test.zim"
    paths: list[pathlib.Path] = []
    with Creator(fpath, "").config_dev_metadata() as creator:
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
                callbacks=Callback(func=delete_callback, kwargs={"fpath": paths[-1]}),
            )
    for path in paths:
        assert not path.exists()


def test_sourcefile_noremoval(tmp_path: pathlib.Path, html_file: pathlib.Path):
    # copy html to folder
    src_path = tmp_path / "source.html"
    shutil.copyfile(html_file, src_path)

    fpath = tmp_path / "test.zim"
    with Creator(fpath, "").config_dev_metadata() as creator:
        creator.add_item(StaticItem(path=src_path.name, filepath=src_path))

    assert src_path.exists()


def test_urlitem_badurl(tmp_path: pathlib.Path):
    with Creator(tmp_path / "test.zim", "").config_dev_metadata() as creator:
        with pytest.raises(IOError, match="Unable to access URL"):
            creator.add_item(URLItem(url="httpo://hello:helloe:hello/"))


def test_urlitem_html(tmp_path: pathlib.Path, gzip_html_url: str):
    file_path = tmp_path / "file.html"
    save_large_file(gzip_html_url, file_path)
    with open(file_path, "rb") as fh:
        file_bytes = fh.read()

    fpath = tmp_path / "test.zim"
    with Creator(fpath, "").config_dev_metadata() as creator:
        creator.add_item(URLItem(url=gzip_html_url))

    zim = Archive(fpath)
    assert bytes(zim.get_item("wiki/Main_Page").content) == file_bytes


def test_urlitem_nonhtmlgzip(tmp_path: pathlib.Path, gzip_nonhtml_url: str):
    file_path = tmp_path / "file.txt"
    save_large_file(gzip_nonhtml_url, file_path)
    with open(file_path, "rb") as fh:
        file_bytes = fh.read()

    fpath = tmp_path / "test.zim"
    with Creator(fpath, "").config_dev_metadata() as creator:
        creator.add_item(URLItem(url=gzip_nonhtml_url))

    with Creator(fpath, "").config_dev_metadata() as creator:
        creator.add_item(URLItem(url=gzip_nonhtml_url, use_disk=True))

    zim = Archive(fpath)
    assert bytes(zim.get_item("robots.txt").content) == file_bytes


def test_urlitem_binary(tmp_path: pathlib.Path, png_image_url: str):
    file_path = tmp_path / "file.png"
    save_large_file(png_image_url, file_path)
    with open(file_path, "rb") as fh:
        file_bytes = fh.read()

    fpath = tmp_path / "test.zim"
    with Creator(fpath, "").config_dev_metadata() as creator:
        creator.add_item(URLItem(url=png_image_url))

    zim = Archive(fpath)
    assert (
        bytes(zim.get_item("static/images/project-logos/commonswiki.png").content)
        == file_bytes
    )


def test_urlitem_staticcontent(tmp_path: pathlib.Path, gzip_nonhtml_url: str):
    fpath = tmp_path / "test.zim"
    with Creator(fpath, "").config_dev_metadata() as creator:
        creator.add_item(URLItem(url=gzip_nonhtml_url, content="hello"))

    zim = Archive(fpath)
    assert bytes(zim.get_item("robots.txt").content) == b"hello"


def test_filelikeprovider_nosize(tmp_path: pathlib.Path, png_image_url: str):
    fileobj = io.BytesIO()
    stream_file(png_image_url, byte_stream=fileobj)

    fpath = tmp_path / "test.zim"
    with Creator(fpath, "").config_dev_metadata() as creator:
        creator.add_item(FileLikeProviderItem(fileobj=fileobj, path="one.png"))

    zim = Archive(fpath)
    assert bytes(zim.get_item("one.png").content) == fileobj.getvalue()


def test_urlprovider(tmp_path: pathlib.Path, png_image_url: str):
    file_path = tmp_path / "file.png"
    save_large_file(png_image_url, file_path)
    with open(file_path, "rb") as fh:
        file_bytes = fh.read()

    fpath = tmp_path / "test.zim"
    with Creator(fpath, "").config_dev_metadata() as creator:
        creator.add_item(SpecialURLProviderItem(url=png_image_url, path="one.png"))

    zim = Archive(fpath)
    assert bytes(zim.get_item("one.png").content) == file_bytes


def test_urlprovider_nolength(
    tmp_path: pathlib.Path, png_image_url: str, png_image: pathlib.Path
):
    # save url's content locally using external tool
    png_image = tmp_path / "original.png"
    save_large_file(png_image_url, png_image)
    with open(png_image, "rb") as fh:
        png_image_bytes = fh.read()

    # create and start an http server without Content-Length support
    server_fpath = tmp_path / "httpd.py"
    port = random.randint(10000, 20000)  # noqa: S311
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
        with (
            tempfile.TemporaryDirectory() as tmp_dir,
            Creator(fpath, "").config_dev_metadata() as creator,
        ):
            tmp_dir = pathlib.Path(tmp_dir)  # noqa: PLW2901
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
                    url=f"http://localhost:{port}/home.png",
                    mimetype="image/png",
                )
            )
    finally:
        httpd.terminate()

    zim = Archive(fpath)
    assert bytes(zim.get_item("home.png").content) == png_image_bytes
    assert bytes(zim.get_item("B").content) == png_image_bytes


def test_item_callback(tmp_path: pathlib.Path, html_file: pathlib.Path):
    fpath = tmp_path / "test.zim"

    class Store:
        called = False

    def cb():
        Store.called = True

    with Creator(fpath, "").config_dev_metadata() as creator:
        creator.add_item(
            StaticItem(path=html_file.name, filepath=html_file),
            callbacks=Callback(func=cb),
        )

    assert Store.called is True


def test_item_callbacks(tmp_path: pathlib.Path):
    fpath = tmp_path / "test.zim"

    class Store:
        called = 0

    def cb():
        Store.called += 1

    with Creator(fpath, "").config_dev_metadata() as creator:
        creator.add_item_for(
            path="hello",
            content="hello",
            callbacks=[Callback(func=cb), Callback(func=cb)],
        )

    assert Store.called == 2

    class UnCallableCallback(Callback):
        @property
        def callable(self) -> bool:
            return False

    with Creator(fpath, "").config_dev_metadata() as creator:
        # +2
        creator.add_item(
            StaticItem(path="hello", content="hello"),
            callbacks=[Callback(func=cb), Callback(func=cb)],
        )
        # + 0
        creator.add_item(StaticItem(path="hello2", content="hello"))
        # +1
        creator.add_item(
            StaticItem(path="hello3", content="hello"),
            callbacks=Callback(func=cb),
        )
        # + 0
        creator.add_item(
            StaticItem(path="hello4", content="hello"),
            callbacks=UnCallableCallback(func=cb),
        )

    assert Store.called == 5


def test_compess_hints(tmp_path: pathlib.Path, html_file: pathlib.Path):
    with Creator(tmp_path / "test.zim", "").config_dev_metadata() as creator:
        creator.add_item_for(
            path=html_file.name,
            fpath=html_file,
            delete_fpath=True,
            should_compress=True,
        )


def test_callback_and_remove(tmp_path: pathlib.Path, html_file: pathlib.Path):
    class Store:
        called = 0

    def cb(*_: Any):
        Store.called += 1

    # duplicate test file as we'll want to remove twice
    html_file2 = html_file.with_suffix(f".2{html_file.suffix}")
    shutil.copyfile(html_file, html_file2)

    with Creator(tmp_path / "test.zim", "").config_dev_metadata() as creator:
        creator.add_item_for(
            path=html_file.name,
            fpath=html_file,
            delete_fpath=True,
            callbacks=Callback(func=cb),
        )
        creator.add_item_for(
            path=html_file2.name,
            fpath=html_file2,
            delete_fpath=True,
            callbacks=Callback(func=cb, args=(html_file.name,)),
        )

    assert not html_file.exists()
    assert Store.called
    assert Store.called == 2


def test_duplicates(tmp_path: pathlib.Path):
    with Creator(tmp_path / "test.zim", "").config_dev_metadata() as creator:
        creator.add_item_for(path="A", content="A")
        creator.add_item_for(path="C", content="C")
        creator.add_redirect(path="B", target_path="A")
        with pytest.raises(RuntimeError, match="existing dirent's title"):
            creator.add_item_for(path="A", content="test2")
        with pytest.raises(RuntimeError, match="existing dirent's title"):
            creator.add_redirect(path="B", target_path="C")


def test_ignore_duplicates(tmp_path: pathlib.Path):
    with Creator(
        tmp_path / "test.zim", "", ignore_duplicates=True
    ).config_dev_metadata() as creator:
        creator.add_item_for(path="A", content="A")
        creator.add_item_for(path="A", content="A2")
        creator.add_redirect(path="B", target_path="A")
        creator.add_redirect(path="B", target_path="C")


def test_without_metadata(tmp_path: pathlib.Path):
    with pytest.raises(ValueError, match="Mandatory metadata are not all set."):
        Creator(tmp_path, "").start()


@pytest.mark.parametrize(
    "tags",
    [
        (
            [
                "wikipedia",
                "_category:wikipedia",
                "_pictures:no",
                "_videos:no",
                "_details:yes",
                "_ftindex:yes",
                "wikipedia;_category:wikipedia;_pictures:no;_videos:no;_details:yes;"
                "_ftindex:yes",
            ]
        ),
    ],
)
@patch("zimscraperlib.zim.creator.logger", autospec=True)
def test_start_logs_metadata_log_contents(
    mocked_logger: logging.Logger,
    png_image: pathlib.Path,
    tags: str | list[str],
    tmp_path: pathlib.Path,
    ignore_metadata_conventions: NoneType,  # noqa: ARG001
):
    mocked_logger.isEnabledFor.side_effect = (  # pyright: ignore[reportFunctionMemberAccess]
        lambda level: level == logging.DEBUG  # pyright: ignore[reportUnknownLambdaType]
    )
    fpath = tmp_path / "test_config.zim"
    with open(png_image, "rb") as fh:
        png_data = fh.read()
    creator = Creator(fpath, "").config_metadata(
        StandardMetadataList(
            Name=NameMetadata("wikipedia_fr_football"),
            Title=TitleMetadata("English Wikipedia"),
            Creator=CreatorMetadata("English speaking Wikipedia contributors"),
            Publisher=PublisherMetadata("Wikipedia user Foobar"),
            Date=DateMetadata(datetime.date(2009, 11, 21)),
            Description=DescriptionMetadata(
                "All articles (without images) from the english Wikipedia"
            ),
            LongDescription=LongDescriptionMetadata(
                "This ZIM file contains all articles (without images)"
                " from the english Wikipedia by 2009-11-10. The topics are..."
            ),
            Language=LanguageMetadata("eng"),
            License=LicenseMetadata("CC-BY"),
            Tags=TagsMetadata(tags),
            Flavour=FlavourMetadata("nopic"),
            Source=SourceMetadata("https://en.wikipedia.org/"),
            Scraper=ScraperMetadata("mwoffliner 1.2.3"),
            Illustration_48x48_at_1=DefaultIllustrationMetadata(png_data),
        ),
        [CustomTextMetadata("TestMetadata", "Test Metadata")],
        fail_on_missing_prefix_in_extras=False,
    )

    class NotPrintable(str):
        def __str__(self):
            raise ValueError("Not printable I said")

    creator._metadata.update(  # pyright: ignore[reportPrivateUsage]
        {
            "Illustration_96x96@1": Metadata(
                value=b"%PDF-1.5\n%\xe2\xe3\xcf\xd3", name="Illustration_96x96@1"
            ),
            "Chars": Metadata(name="Chars", value=b"\xc5\xa1\xc9\x94\xc9\x9b"),
            "Chars-32": Metadata(
                name="Chars-32",
                value=b"\xff\xfe\x00\x00a\x01\x00\x00T\x02\x00\x00[\x02\x00\x00",
            ),
            "Video": Metadata(
                name="Video",
                value=b"\x00\x00\x00 ftypisom\x00\x00\x02\x00isomiso2avc1mp41\x00",
            ),
            "Toupie": CustomTextMetadata("Toupie", NotPrintable("value")),
        }  # intentionaly bad, to handle case where user does bad things
    )
    # intentionaly bad, to handle case where user does bad things
    creator._metadata[  # pyright: ignore[reportArgumentType, reportPrivateUsage]
        "Relation"
    ] = None
    creator._metadata[  # pyright: ignore[reportArgumentType, reportPrivateUsage]
        "BadRawValue"
    ] = "Value"
    creator._log_metadata()  # pyright: ignore[reportPrivateUsage]
    mocked_logger.debug.assert_has_calls(  # pyright: ignore[reportFunctionMemberAccess]
        [
            call("Metadata: BadRawValue is improper metadata type: str: Value"),
            call("Metadata: Chars = šɔɛ"),
            call(
                "Metadata: Chars-32 is a 16 bytes text/plain blob "
                "not decodable as an UTF-8 string"
            ),
            call("Metadata: Creator = English speaking Wikipedia contributors"),
            call("Metadata: Date = 2009-11-21"),
            call(
                "Metadata: Description = All articles (without images) from the "
                "english Wikipedia"
            ),
            call("Metadata: Flavour = nopic"),
            call("Metadata: Illustration_48x48@1 is a 3274 bytes 48x48px PNG Image"),
            call("Metadata: Illustration_96x96@1 is a 14 bytes application/pdf blob"),
            call("Metadata: Language = ['eng']"),
            call("Metadata: License = CC-BY"),
            call(
                "Metadata: LongDescription = This ZIM file contains all articles "
                "(without images) from the english Wikipedia by 2009-11-10. "
                "The topics are..."
            ),
            call("Metadata: Name = wikipedia_fr_football"),
            call("Metadata: Publisher = Wikipedia user Foobar"),
            call("Metadata: Relation is improper metadata type: NoneType: None"),
            call("Metadata: Scraper = mwoffliner 1.2.3"),
            call("Metadata: Source = https://en.wikipedia.org/"),
            call(f"Metadata: Tags = {tags}"),
            call("Metadata: TestMetadata = Test Metadata"),
            call("Metadata: Title = English Wikipedia"),
            # cleaned-up anyway
            call("Metadata: Toupie = value"),
            call("Metadata: Video is a 33 bytes video/mp4 blob"),
        ]
    )


def test_relax_metadata(
    tmp_path: pathlib.Path,
    ignore_metadata_conventions: NoneType,  # noqa: ARG001
):
    Creator(tmp_path, "").config_dev_metadata(DescriptionMetadata("T" * 90)).start()


@pytest.mark.parametrize(
    "tags",
    [
        (
            "wikipedia;_category:wikipedia;_pictures:no;_videos:no;_details:yes;"
            "_ftindex:yes"
        ),
        (
            [
                "wikipedia",
                "_category:wikipedia",
                "_pictures:no",
                "_videos:no",
                "_details:yes",
                "_ftindex:yes",
            ]
        ),
    ],
)
def test_config_metadata(
    tmp_path: pathlib.Path, png_image: pathlib.Path, tags: str | list[str]
):
    fpath = tmp_path / "test_config.zim"
    with open(png_image, "rb") as fh:
        png_data = fh.read()
    creator = Creator(fpath, "").config_metadata(
        StandardMetadataList(
            Name=NameMetadata("wikipedia_fr_football"),
            Title=TitleMetadata("English Wikipedia"),
            Creator=CreatorMetadata("English speaking Wikipedia contributors"),
            Publisher=PublisherMetadata("Wikipedia user Foobar"),
            Date=DateMetadata(datetime.date(2009, 11, 21)),
            Description=DescriptionMetadata(
                "All articles (without images) from the english Wikipedia"
            ),
            LongDescription=LongDescriptionMetadata(
                "This ZIM file contains all articles (without images)"
                " from the english Wikipedia by 2009-11-10. The topics are..."
            ),
            Language=LanguageMetadata("eng"),
            License=LicenseMetadata("CC-BY"),
            Tags=TagsMetadata(tags),
            Flavour=FlavourMetadata("nopic"),
            Source=SourceMetadata("https://en.wikipedia.org/"),
            Scraper=ScraperMetadata("mwoffliner 1.2.3"),
            Illustration_48x48_at_1=DefaultIllustrationMetadata(png_data),
        ),
        [CustomTextMetadata("X-TestMetadata", "Test Metadata")],
    )
    with creator:
        pass

    assert fpath.exists()

    reader = Archive(fpath)
    assert reader.get_text_metadata("Name") == "wikipedia_fr_football"
    assert reader.get_text_metadata("Title") == "English Wikipedia"
    assert (
        reader.get_text_metadata("Creator") == "English speaking Wikipedia contributors"
    )
    assert reader.get_text_metadata("Publisher") == "Wikipedia user Foobar"
    assert reader.get_text_metadata("Date") == "2009-11-21"
    assert (
        reader.get_text_metadata("Description")
        == "All articles (without images) from the english Wikipedia"
    )
    assert (
        reader.get_text_metadata("LongDescription")
        == "This ZIM file contains all articles (without images)"
        " from the english Wikipedia by 2009-11-10. The topics are..."
    )
    assert reader.get_text_metadata("Language") == "eng"
    assert reader.get_text_metadata("License") == "CC-BY"
    assert set(reader.get_text_metadata("Tags").split(";")) == set(
        "wikipedia;_category:wikipedia;_pictures:no;_videos:no;"
        "_details:yes;_ftindex:yes".split(";")
    )  # order of tags is not guaranteed and does not matter
    assert len(reader.get_text_metadata("Tags").split(";")) == 6
    assert reader.get_text_metadata("Flavour") == "nopic"
    assert reader.get_text_metadata("Source") == "https://en.wikipedia.org/"
    assert reader.get_text_metadata("Scraper") == "mwoffliner 1.2.3"
    assert reader.get_metadata("Illustration_48x48@1") == png_data
    assert reader.get_text_metadata("X-TestMetadata") == "Test Metadata"


def test_config_metadata_control_characters(tmp_path: pathlib.Path):
    fpath = tmp_path / "test_config.zim"
    creator = Creator(fpath, "").config_dev_metadata(
        [
            DescriptionMetadata(
                "\t\n\r\n \tA description \awith  \bcontrol characters\v"
            ),
            LongDescriptionMetadata(
                "A description \rwith \a\ncontrol characters\tsss\t\n\r\n \t"
            ),
            CreatorMetadata("  A creator "),
        ]
    )
    with creator:
        creator.add_metadata(
            CustomTextMetadata(
                "Description_1",
                "\t\n\r\n \tA description \awith  \bcontrol characters\v",
            )
        )
        creator.add_metadata(
            CustomTextMetadata(
                "LongDescription_1",
                "A description \rwith \a\ncontrol characters\tsss\t\n\r\n \t",
            )
        )
        creator.add_metadata(CustomTextMetadata("Creator_1", "  A creator "))
        creator.add_metadata(CustomMetadata("Binary1", bytes.fromhex("01FA")))
        pass

    assert fpath.exists()

    reader = Archive(fpath)
    assert (
        reader.get_text_metadata("Description")
        == "A description with  control characters"
    )
    assert (
        reader.get_text_metadata("LongDescription")
        == "A description \rwith \ncontrol characters\tsss"
    )
    assert reader.get_text_metadata("Creator") == "A creator"
    assert (
        reader.get_text_metadata("Description_1")
        == "A description with  control characters"
    )
    assert (
        reader.get_text_metadata("LongDescription_1")
        == "A description \rwith \ncontrol characters\tsss"
    )
    assert reader.get_text_metadata("Creator_1") == "A creator"
    assert bytes.hex(reader.get_metadata("Binary1")) == "01fa"


class ExtraMetadataCase(NamedTuple):
    extras: list[AnyMetadata]
    fail_on_missing_prefix: bool
    id: str


def __get_extra_metadata_case_id(case: ExtraMetadataCase) -> str:
    return case.id


@pytest.fixture(
    params=[
        ExtraMetadataCase(
            [CustomTextMetadata("X-TestMetadata", "Test Metadata")],
            True,
            id="good_prefix",
        ),
        ExtraMetadataCase(
            [CustomTextMetadata("TestMetadata", "Test Metadata")],
            False,
            id="bad_prefix",
        ),
        ExtraMetadataCase(
            [
                CustomTextMetadata("X-TestMetadata", "Test Metadata"),
                CustomTextMetadata("X-TestMetadata2", "Test Metadata"),
            ],
            True,
            id="list_of_two_good_prefix",
        ),
        ExtraMetadataCase(
            [
                CustomTextMetadata("X-TestMetadata", "Test Metadata"),
                CustomTextMetadata("TestMetadata2", "Test Metadata"),
            ],
            False,
            id="list_with_one_bad_prefix",
        ),
    ],
    ids=__get_extra_metadata_case_id,
)
def metadata_extras(request: pytest.FixtureRequest):
    yield request.param


def test_metadata_extras(tmp_path: pathlib.Path, metadata_extras: ExtraMetadataCase):
    Creator(tmp_path / "_.zim", "").config_metadata(
        DEFAULT_DEV_ZIM_METADATA,
        metadata_extras.extras,
        fail_on_missing_prefix_in_extras=metadata_extras.fail_on_missing_prefix,
    )


def test_metadata_extras_dev(
    tmp_path: pathlib.Path, metadata_extras: ExtraMetadataCase
):
    Creator(tmp_path / "_.zim", "").config_dev_metadata(metadata_extras.extras)


def test_metadata_extras_missing_prefix(tmp_path: pathlib.Path):
    with pytest.raises(ValueError, match="does not starts with X- as expected"):
        Creator(tmp_path / "_.zim", "").config_metadata(
            DEFAULT_DEV_ZIM_METADATA,
            [CustomTextMetadata("TestMetadata", "Test Metadata")],
        )


@pytest.mark.parametrize(
    "name,metadata,expected_value",
    [
        pytest.param(
            "X-Test",
            CustomTextMetadata(
                "X-Test", DEFAULT_DEV_ZIM_METADATA.Title.libzim_value.decode() + "Foo"
            ),
            DEFAULT_DEV_ZIM_METADATA.Title.libzim_value.decode() + "Foo",
            id="simple_str",
        ),
        pytest.param("Tags", TagsMetadata(["tag1", "tag2"]), "tag1;tag2", id="tags"),
    ],
)
def test_add_metadata(
    tmp_path: pathlib.Path, name: str, metadata: AnyMetadata, expected_value: str
):
    fpath = tmp_path / "test_blank.zim"
    with Creator(fpath, "").config_dev_metadata() as creator:
        creator.add_metadata(metadata)
    assert fpath.exists()
    reader = Archive(fpath)
    assert reader.get_text_metadata(name) == expected_value


def test_config_indexing(tmp_path: pathlib.Path):
    with pytest.raises(ValueError):
        Creator(tmp_path / "_.zim", "").config_indexing(True, "fr")
    with pytest.raises(ValueError):
        Creator(tmp_path / "_.zim", "").config_indexing(True, "")
    assert Creator(tmp_path / "_.zim", "").config_indexing(True, "fra")
    assert Creator(tmp_path / "_.zim", "").config_indexing(True, "bam")
    assert Creator(tmp_path / "_.zim", "").config_indexing(False, "bam")
    assert Creator(tmp_path / "_.zim", "").config_indexing(False)
