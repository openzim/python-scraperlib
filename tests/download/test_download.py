#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import pytest
import requests

from zimscraperlib.download import save_file, save_large_file


def assert_downloaded_file(url, file):
    assert file.exists()
    # our google test urls dont support HEAD
    req = requests.get(url)
    # we test against binary response: Content-Length not accurate as gzip-encoded
    assert file.stat().st_size == len(req.content)


def get_dest_file(tmp_path):
    return tmp_path.joinpath("favicon.ico")


def test_missing_dest(tmp_path):
    with pytest.raises(TypeError):
        save_file("http://some_url")


def test_invalid_url(tmp_path, invalid_url):
    dest_file = tmp_path / "favicon.ico"
    with pytest.raises(requests.exceptions.ConnectionError):
        save_file(invalid_url, dest_file)


@pytest.mark.slow
def test_save_http(tmp_path, valid_http_url):
    dest_file = tmp_path / "favicon.ico"
    save_file(valid_http_url, dest_file)
    assert_downloaded_file(valid_http_url, dest_file)


@pytest.mark.slow
def test_save_https(tmp_path, valid_https_url):
    dest_file = tmp_path / "favicon.ico"
    save_file(valid_https_url, dest_file)
    assert_downloaded_file(valid_https_url, dest_file)


@pytest.mark.slow
def test_save_parent_folder_missing(tmp_path, valid_http_url):
    dest_file = tmp_path / "some-folder" / "favicon.ico"
    save_file(valid_http_url, dest_file)
    assert_downloaded_file(valid_http_url, dest_file)


@pytest.mark.slow
def test_large_download_http(tmp_path, valid_http_url):
    dest_file = tmp_path / "favicon.ico"
    save_large_file(valid_http_url, dest_file)
    assert_downloaded_file(valid_http_url, dest_file)


@pytest.mark.slow
def test_large_download_https(tmp_path, valid_https_url):
    dest_file = tmp_path / "favicon.ico"
    save_large_file(valid_https_url, dest_file)
    assert_downloaded_file(valid_https_url, dest_file)
