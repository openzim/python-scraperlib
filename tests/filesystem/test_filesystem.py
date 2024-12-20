import pathlib
from tempfile import TemporaryDirectory
from typing import Any

import magic
import pytest

from zimscraperlib.filesystem import (
    delete_callback,
    get_content_mimetype,
    get_file_mimetype,
    path_from,
)


def test_file_mimetype(png_image: pathlib.Path, jpg_image: pathlib.Path):
    assert get_file_mimetype(png_image) == "image/png"
    assert get_file_mimetype(jpg_image) == "image/jpeg"


def test_content_mimetype(png_image: pathlib.Path, jpg_image: pathlib.Path):
    with open(png_image, "rb") as fh:
        assert get_content_mimetype(fh.read(64)) == "image/png"

    with open(jpg_image, "rb") as fh:
        assert get_content_mimetype(fh.read(64)) == "image/jpeg"


def test_content_mimetype_fallback(
    monkeypatch: pytest.MonkeyPatch, undecodable_byte_stream: bytes
):
    # use raw function first to test actual code
    assert get_content_mimetype(undecodable_byte_stream) == "application/octet-stream"

    # mock then so we keep coverage on systems where magic works
    def raising_magic(*args: Any, **kwargs: Any):  # noqa: ARG001
        raise UnicodeDecodeError("nocodec", b"", 0, 1, "noreason")

    monkeypatch.setattr(magic, "from_buffer", raising_magic)
    assert get_content_mimetype(undecodable_byte_stream) == "application/octet-stream"


def test_mime_overrides(svg_image: pathlib.Path):
    mime_map = [(svg_image, "image/svg+xml")]
    for fpath, expected_mime in mime_map:
        assert get_file_mimetype(fpath) == expected_mime
        with open(fpath, "rb") as fh:
            assert get_content_mimetype(fh.read(64)) == expected_mime


def test_delete_callback(tmp_path: pathlib.Path):
    fpath = tmp_path.joinpath("my-file")
    with open(fpath, "w") as fh:
        fh.write("content")

    delete_callback(fpath)

    assert not fpath.exists()

    # file already gone should not be a problem
    delete_callback(fpath)

    # wrong path should not be a problem
    delete_callback(pathlib.Path("/foo.txt"))


def test_path_from_tmp_dir():
    tempdir = TemporaryDirectory()
    with path_from(tempdir) as tmp_dir:
        file = tmp_dir / "file.txt"
        file.touch()
        assert file.exists()
        assert pathlib.Path(tempdir.name).exists()

    assert not pathlib.Path(tempdir.name).exists()


def test_path_from_path():
    tempdir = TemporaryDirectory()
    tempdir_path = pathlib.Path(tempdir.name)
    with path_from(tempdir_path) as tmp_dir:
        file = tmp_dir / "file.txt"
        file.touch()
        assert file.exists()
        assert pathlib.Path(tempdir.name).exists()

    assert pathlib.Path(tempdir.name).exists()
    tempdir.cleanup()
    assert not pathlib.Path(tempdir.name).exists()


def test_path_from_str():
    tempdir = TemporaryDirectory()
    tempdir_path = pathlib.Path(tempdir.name)
    with path_from(str(tempdir_path)) as tmp_dir:
        file = tmp_dir / "file.txt"
        file.touch()
        assert file.exists()
        assert pathlib.Path(tempdir.name).exists()

    assert pathlib.Path(tempdir.name).exists()
    tempdir.cleanup()
    assert not pathlib.Path(tempdir.name).exists()
