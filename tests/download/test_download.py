#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import concurrent.futures
import io
import pathlib

import pytest
import requests

from zimscraperlib.download import (
    BestMp4,
    BestWebm,
    YoutubeDownloader,
    save_large_file,
    stream_file,
)


def assert_downloaded_file(url, file):
    assert file.exists()
    # our google test urls dont support HEAD
    req = requests.get(url)
    # we test against binary response: Content-Length not accurate as gzip-encoded
    assert file.stat().st_size == len(req.content)


def assert_headers(returned_headers):
    assert isinstance(returned_headers, requests.structures.CaseInsensitiveDict)
    assert returned_headers["Content-Type"] == "image/x-icon"


def get_dest_file(tmp_path):
    return tmp_path.joinpath("favicon.ico")


def test_missing_dest(tmp_path):
    with pytest.raises(requests.exceptions.ConnectionError):
        stream_file(url="http://some_url", byte_stream=io.BytesIO())


def test_invalid_url(tmp_path, invalid_url):
    dest_file = tmp_path / "favicon.ico"
    with pytest.raises(requests.exceptions.ConnectionError):
        stream_file(url=invalid_url, fpath=dest_file)


def test_no_output_supplied(valid_http_url):
    with pytest.raises(
        ValueError, match="Either file path or a bytesIO object is needed"
    ):
        stream_file(url=valid_http_url)


def test_first_block_download(valid_http_url):
    byte_stream = io.BytesIO()
    size, ret = stream_file(
        url=valid_http_url, byte_stream=byte_stream, only_first_block=True
    )
    assert_headers(ret)
    # valid_http_url randomly returns gzip-encoded content.
    # otherwise, expected size is default block size
    expected = 3062 if ret.get("Content-Encoding") == "gzip" else 1024
    assert len(byte_stream.read()) <= expected


@pytest.mark.slow
def test_save_http(tmp_path, valid_http_url):
    dest_file = tmp_path / "favicon.ico"
    size, ret = stream_file(url=valid_http_url, fpath=dest_file)
    assert_headers(ret)
    assert_downloaded_file(valid_http_url, dest_file)


@pytest.mark.slow
def test_save_https(tmp_path, valid_https_url):
    dest_file = tmp_path / "favicon.ico"
    size, ret = stream_file(url=valid_https_url, fpath=dest_file)
    assert_headers(ret)
    assert_downloaded_file(valid_https_url, dest_file)


@pytest.mark.slow
def test_stream_to_bytes(valid_https_url):
    byte_stream = io.BytesIO()
    size, ret = stream_file(url=valid_https_url, byte_stream=byte_stream)
    assert_headers(ret)
    assert byte_stream.read() == requests.get(valid_https_url).content


@pytest.mark.slow
def test_save_parent_folder_missing(tmp_path, valid_http_url):
    dest_file = tmp_path / "some-folder" / "favicon.ico"
    with pytest.raises(IOError):
        stream_file(url=valid_http_url, fpath=dest_file)


@pytest.mark.slow
def test_save_http_error(tmp_path, http_error_url):
    dest_file = tmp_path / "favicon.ico"
    with pytest.raises(requests.exceptions.HTTPError):
        stream_file(url=http_error_url, fpath=dest_file)


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


@pytest.mark.slow
@pytest.mark.parametrize(
    "url,video_id",
    [
        ("Bc5QSUhL6co", "Bc5QSUhL6co"),
        ("www.youtube.com/watch?v=Bc5QSUhL6co", "Bc5QSUhL6co"),
        ("https://www.youtube.com/watch?v=Bc5QSUhL6co", "Bc5QSUhL6co"),
    ],
)
def test_youtube_download_serial(url, video_id, tmp_path):
    yt_downloader = YoutubeDownloader(threads=1)
    options = BestWebm.get_options(
        target_dir=tmp_path,
        filepath=pathlib.Path("%(id)s/video.%(ext)s"),
    )
    yt_downloader.download(url, options)
    assert tmp_path.joinpath(video_id).joinpath("video.webm").exists()
    yt_downloader.shutdown()


@pytest.mark.slow
def test_youtube_download_nowait(tmp_path):
    with YoutubeDownloader(threads=1) as yt_downloader:
        future = yt_downloader.download(
            "Bc5QSUhL6co", BestMp4.get_options(target_dir=tmp_path), wait=False
        )
        assert future.running()
        assert not yt_downloader.executor._shutdown
        done, not_done = concurrent.futures.wait(
            [future], return_when=concurrent.futures.ALL_COMPLETED
        )
        assert future.exception() is None
        assert len(done) == 1
        assert len(not_done) == 0


@pytest.mark.slow
def test_youtube_download_error(tmp_path):
    yt_downloader = YoutubeDownloader(threads=1)
    with pytest.raises(Exception):
        yt_downloader.download("11", BestMp4.get_options())
    yt_downloader.shutdown()


@pytest.mark.slow
def test_youtube_download_contextmanager(tmp_path):
    with YoutubeDownloader(threads=1) as yt_downloader:
        yt_downloader.download("Bc5QSUhL6co", BestMp4.get_options(target_dir=tmp_path))
    assert yt_downloader.executor._shutdown
    assert tmp_path.joinpath("video.mp4").exists()
