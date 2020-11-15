#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import io
import pytest
import requests
import pathlib
import concurrent.futures

from zimscraperlib.download import (
    stream_file,
    save_large_file,
    YoutubeDownloader,
    BestWebm,
    BestMp4,
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
    with pytest.raises(ValueError, match="Either file path or a bytesIO object is needed"):
        stream_file(url=valid_http_url)


# @pytest.mark.slow
# def test_show_progress(tmp_path, valid_http_url):
#     dest_file = tmp_path / "favicon.ico"
#     local_logger = getLogger()
#     stream_file(url=valid_http_url, fpath=dest_file, logger_obj=local_logger)



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
def test_stream_to_bytes(tmp_path, valid_https_url):
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
def test_youtube_download_parallel(tmp_path):
    def download_and_assert(url, outtmpl, yt_downloader):
        options = BestMp4.get_options(
            filepath=outtmpl,
        )
        yt_downloader.download(url, options)
        assert outtmpl.with_suffix(".mp4").exists()

    yt_downloader = YoutubeDownloader(threads=2)
    videos = {
        "Bc5QSUhL6co": tmp_path / "video1.%(ext)s",
        "a3HZ8S2H-GQ": tmp_path / "video2.%(ext)s",
        "3HFBR0UQPes": tmp_path / "video3.%(ext)s",
        "oiWWKumrLH8": tmp_path / "video4.%(ext)s",
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
        yt_downloader.download("11", BestMp4.get_options())
    yt_downloader.shutdown()


@pytest.mark.slow
@pytest.mark.parametrize(
    "nb_workers,videos",
    [
        (1, ["Bc5QSUhL6co"]),
        (2, ["Bc5QSUhL6co", "a3HZ8S2H-GQ"]),
    ],
)
def test_youtube_download_contextmanager(nb_workers, videos, tmp_path):
    with YoutubeDownloader(threads=nb_workers) as yt_downloader:
        assert yt_downloader.executor._max_workers == nb_workers
        yt_downloader.download("Bc5QSUhL6co", BestMp4.get_options(target_dir=tmp_path))
        fs = [
            yt_downloader.download(
                video, BestMp4.get_options(target_dir=tmp_path), wait=False
            )
            for video in videos
        ]
        done, not_done = concurrent.futures.wait(
            fs, return_when=concurrent.futures.ALL_COMPLETED
        )
        assert len(done) == len(videos) and len(not_done) == 0
