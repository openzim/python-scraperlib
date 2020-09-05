#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import pytest
import requests
import concurrent.futures

from zimscraperlib.download import save_file, save_large_file, YoutubeDownloader


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
    with pytest.raises(TypeError):
        save_file("http://some_url")


def test_invalid_url(tmp_path, invalid_url):
    dest_file = tmp_path / "favicon.ico"
    with pytest.raises(requests.exceptions.ConnectionError):
        save_file(invalid_url, dest_file)


@pytest.mark.slow
def test_save_http(tmp_path, valid_http_url):
    dest_file = tmp_path / "favicon.ico"
    ret = save_file(valid_http_url, dest_file)
    assert_headers(ret)
    assert_downloaded_file(valid_http_url, dest_file)


@pytest.mark.slow
def test_save_https(tmp_path, valid_https_url):
    dest_file = tmp_path / "favicon.ico"
    ret = save_file(valid_https_url, dest_file)
    assert_headers(ret)
    assert_downloaded_file(valid_https_url, dest_file)


@pytest.mark.slow
def test_save_parent_folder_missing(tmp_path, valid_http_url):
    dest_file = tmp_path / "some-folder" / "favicon.ico"
    with pytest.raises(IOError):
        save_file(valid_http_url, dest_file)


@pytest.mark.slow
def test_save_http_error(tmp_path, http_error_url):
    dest_file = tmp_path / "favicon.ico"
    with pytest.raises(requests.exceptions.HTTPError):
        save_file(http_error_url, dest_file)


@pytest.mark.slow
def test_save_timeout(tmp_path, timeout_url):
    dest_file = tmp_path / "favicon.ico"
    with pytest.raises(requests.exceptions.RequestException):
        save_file(timeout_url, dest_file, timeout=1)


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
    "url,filename",
    [
        ("Bc5QSUhL6co", "video1.mp4"),
        ("www.youtube.com/watch?v=Bc5QSUhL6co", "video2.mp4"),
        ("https://www.youtube.com/watch?v=Bc5QSUhL6co", "video3.mp4"),
    ],
)
def test_youtube_download_serial(url, filename, tmp_path):
    yt_downloader = YoutubeDownloader(threads=1)
    fpath = tmp_path / filename
    downloaded_file = yt_downloader.download(url, fpath)
    assert downloaded_file.exists()
    yt_downloader.shutdown()


@pytest.mark.slow
def test_youtube_download_parallel(tmp_path):
    def download_and_assert(url, video_path, yt_downloader):
        downloaded_file = yt_downloader.download(url, video_path)
        assert downloaded_file.exists()

    yt_downloader = YoutubeDownloader(threads=2)
    videos = {
        "Bc5QSUhL6co": tmp_path / "video1.mp4",
        "a3HZ8S2H-GQ": tmp_path / "video2.mp4",
        "3HFBR0UQPes": tmp_path / "video3.mp4",
        "oiWWKumrLH8": tmp_path / "video4.mp4",
    }
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        fs = [
            executor.submit(download_and_assert, key, val, yt_downloader)
            for key, val in videos.items()
        ]
        done, not_done = concurrent.futures.wait(
            fs, return_when=concurrent.futures.ALL_COMPLETED
        )
        assert len(done) == 4
        for future in done:
            assert future.exception() is None
    yt_downloader.shutdown()


@pytest.mark.slow
def test_youtube_download_error(tmp_path):
    yt_downloader = YoutubeDownloader(threads=1)
    with pytest.raises(Exception):
        yt_downloader.download("11", tmp_path / "video.mp4")
    yt_downloader.shutdown()
