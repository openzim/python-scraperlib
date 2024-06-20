#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 nu

import shutil
import subprocess
import sys

import pytest

from zimscraperlib.zim.archive import Archive
from zimscraperlib.zim.filesystem import (
    FileItem,
    IncorrectZIMFilenameError,
    MissingZIMFolderError,
    NotADirectoryZIMFolderError,
    NotWritableZIMFolderError,
    make_zim_file,
    validate_zimfile_creatable,
)


def test_fileitem(tmp_path, png_image):
    fpath = tmp_path / png_image.name
    shutil.copyfile(png_image, fpath)

    # ensure all properties of a FileItem representing a binary are correct
    article = FileItem(tmp_path, fpath)
    assert article.get_path() == "commons48.png"
    assert article.get_title() == ""
    assert article.get_mimetype() == "image/png"


def test_redirects_file(tmp_path, png_image, build_data):
    build_data["build_dir"].mkdir()
    shutil.copyfile(png_image, build_data["build_dir"] / png_image.name)
    build_data["redirects_file"] = tmp_path / "toto.tsv"
    with open(build_data["redirects_file"], "w") as fh:
        # write a redirect with a namespace (old ns scheme)
        fh.write("A\tAccueil\t\tcommons48.png\n")

    # call make_zim_file with redirects_file
    make_zim_file(
        build_dir=build_data["build_dir"],
        fpath=build_data["fpath"],
        name="test-zim",
        main_page="welcome",
        illustration=png_image.name,
        title="Test ZIM",
        description="A test ZIM",
        redirects_file=build_data["redirects_file"],
    )


def test_make_zim_file_fail_nobuildir(build_data):
    # ensure we fail on missing build dir
    with pytest.raises(IOError):
        make_zim_file(**build_data)
    assert not build_data["fpath"].exists()


def test_make_zim_file_fail_noillustration(build_data):
    # ensure we fail on missing illustration
    build_data["build_dir"].mkdir()
    with pytest.raises(IOError):
        make_zim_file(**build_data)
    assert not build_data["fpath"].exists()


@pytest.mark.parametrize(
    "with_redirects, with_redirects_file",
    [(True, True), (True, False), (False, True), (False, False)],
)
def test_make_zim_file_working(
    build_data, png_image, with_redirects, with_redirects_file
):
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

    if not with_redirects:
        build_data.pop("redirects")
    if not with_redirects_file:
        build_data.pop("redirects_file")
    make_zim_file(**build_data)
    assert build_data["fpath"].exists()
    reader = Archive(build_data["fpath"])
    expected_entry_count = 4
    if with_redirects:
        expected_entry_count += 1
    if with_redirects_file:
        expected_entry_count += 3

    assert reader.entry_count == expected_entry_count

    assert reader.get_item("style.css").mimetype == "text/css"
    assert reader.get_item("app.js").mimetype in (
        "text/javascript",
        "application/javascript",
    )
    assert reader.get_suggestions_count("bienvenue") == 0
    assert reader.get_suggestions_count("coucou") == 1
    assert "welcome" in list(reader.get_suggestions("coucou"))


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
        illustration="{png_image.name}",
        title="Test ZIM",
        description="A test ZIM",
        redirects_file="{build_data["redirects_file"]}")
except Exception as exc:
    print(exc)
finally:
    print("Program exiting")
"""

    py = subprocess.run([sys.executable, "-c", pycode], check=False)
    # returncode will be either 0 or -11, depending on garbage collection
    # in scrapers, we want to be able to fail on errors and absolutely don't want to
    # create a ZIM file, so SEGFAULT on exit it (somewhat) OK
    assert py.returncode in (0, 11, -6, -11)  # SIGSEV is 11
    assert not build_data["fpath"].exists()


@pytest.fixture(scope="module")
def valid_zim_filename():
    return "myfile.zim"


def test_validate_zimfile_creatable_ok(tmp_path, valid_zim_filename):

    validate_zimfile_creatable(tmp_path, valid_zim_filename)


def test_validate_zimfile_creatable_folder_not_exists(tmp_path, valid_zim_filename):

    with pytest.raises(MissingZIMFolderError):
        validate_zimfile_creatable(tmp_path / "foo", valid_zim_filename)


def test_validate_zimfile_creatable_bad_folder(tmp_path, valid_zim_filename):

    with pytest.raises(NotADirectoryZIMFolderError):
        (tmp_path / "foo.txt").touch()
        validate_zimfile_creatable(tmp_path / "foo.txt", valid_zim_filename)


def test_validate_zimfile_creatable_folder_not_writable(tmp_path, valid_zim_filename):

    with pytest.raises(NotWritableZIMFolderError):
        (tmp_path / "foo").mkdir(mode=111)
        validate_zimfile_creatable(tmp_path / "foo", valid_zim_filename)


def test_validate_zimfile_creatable_bad_name(tmp_path):

    with pytest.raises(IncorrectZIMFilenameError):
        validate_zimfile_creatable(tmp_path, "t\0t\0.zim")
