#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import pathlib

import pytest

from zimscraperlib.inputs import handle_user_provided_file


def test_with_none():
    assert handle_user_provided_file(source=None) is None


def test_empty_value():
    assert handle_user_provided_file(source=" ") is None


def test_missing_local():
    with pytest.raises(IOError):
        handle_user_provided_file(source="/some/incorrect/path.txt")


def test_local_copy(png_image):
    fpath = handle_user_provided_file(source=str(png_image))
    assert fpath is not None
    assert fpath.exists()
    assert fpath.suffix == png_image.suffix
    assert fpath.stat().st_size == png_image.stat().st_size


def test_local_nocopy(png_image):
    fpath = handle_user_provided_file(source=str(png_image), nocopy=True)
    assert fpath is not None
    assert fpath.exists()
    assert str(fpath) == str(png_image)


def test_remote(valid_http_url):
    fpath = handle_user_provided_file(source=valid_http_url)
    assert fpath is not None
    assert fpath.exists()
    assert fpath.suffix == pathlib.Path(valid_http_url).suffix


def test_local_dest(tmp_path, png_image):
    dest = tmp_path / png_image.name
    fpath = handle_user_provided_file(source=str(png_image), dest=dest)
    assert fpath is not None
    assert fpath.exists()
    assert fpath == dest


def test_remote_dest(tmp_path, valid_http_url):
    dest = tmp_path / pathlib.Path(valid_http_url).name
    fpath = handle_user_provided_file(source=valid_http_url, dest=dest)
    assert fpath is not None
    assert fpath.exists()
    assert fpath == dest


def test_local_indir(tmp_path, png_image):
    fpath = handle_user_provided_file(source=str(png_image), in_dir=tmp_path)
    assert fpath is not None
    assert fpath.exists()
    assert fpath.parent == tmp_path


def test_remote_indir(tmp_path, valid_http_url):
    fpath = handle_user_provided_file(source=valid_http_url, in_dir=tmp_path)
    assert fpath is not None
    assert fpath.exists()
    assert fpath.parent == tmp_path
