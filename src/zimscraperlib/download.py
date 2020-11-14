#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import io
import pathlib
import subprocess
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Optional, Union
from logging import Logger

import requests
import youtube_dl

from . import logger


class YoutubeDownloader:
    """A class to download youtube videos using youtube_dl, on a ThreadPoolExecutor
    maintaining a specified number of workers, even when executed parallely with
    a higher number of workers. The shutdown method must be run explicitly to
    free any occupied resources"""

    def __init__(self, threads: Optional[int] = 2) -> None:
        """Initialize the class
        Arguments:
        threads: The max number of workers for the executor"""

        self.executor = ThreadPoolExecutor(max_workers=threads)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.shutdown()

    def shutdown(self) -> None:
        """ shuts down the executor """

        self.executor.shutdown(wait=True)

    def _run_youtube_dl(self, url: str, options: dict) -> None:
        with youtube_dl.YoutubeDL(options) as ydl:
            ydl.download([url])

    def download(
        self,
        url: str,
        options: Optional[dict],
        wait: Optional[bool] = True,
    ) -> Union[bool, Future]:
        """Downloads a video using run_youtube_dl on the initialized executor.

        Arguments:
        url: The url/video ID of the video to download.
        options: A dict containing any options that you want to pass directly to youtube_dl
        wait: A boolean to specify whether to wait for completion. In case wait is False, the method would return a Future object"""

        future = self.executor.submit(self._run_youtube_dl, url, options)
        if not wait:
            return future
        if not future.exception():
            # return the result
            return future.result()
        # raise the exception
        raise future.exception()


class YoutubeConfig(dict):
    options = {}
    defaults = {
        "writethumbnail": True,
        "write_all_thumbnails": True,
        "writesubtitles": True,
        "allsubtitles": True,
        "subtitlesformat": "vtt",
        "keepvideo": False,
        "ignoreerrors": False,
        "retries": 20,
        "fragment-retries": 50,
        "skip-unavailable-fragments": True,
        "outtmpl": "video.%(ext)s",
    }

    def __init__(self, **kwargs):
        super().__init__(self, **type(self).defaults)
        self.update(self.options)
        self.update(kwargs)

    @classmethod
    def get_options(
        cls,
        target_dir: Optional[pathlib.Path] = None,
        filepath: Optional[pathlib.Path] = None,
        **options,
    ):
        if "outtmpl" not in options:
            outtmpl = cls.options.get("outtmpl", cls.defaults["outtmpl"])
            if filepath:
                outtmpl = str(filepath)
            # send output to target_dir
            if target_dir:
                outtmpl = str(target_dir.joinpath(outtmpl))
            options["outtmpl"] = outtmpl

        config = cls()
        config.update(options)
        return config


class BestWebm(YoutubeConfig):
    options = {
        "preferredcodec": "webm",
        "format": "best[ext=webm]/bestvideo[ext=webm]+bestaudio[ext=webm]/best",
    }


class BestMp4(YoutubeConfig):
    options = {
        "preferredcodec": "mp4",
        "format": "best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best",
    }


def save_large_file(url: str, fpath: pathlib.Path) -> None:
    """ download a binary file from its URL, using wget """
    subprocess.run(
        [
            "/usr/bin/env",
            "wget",
            "-t",
            "5",
            "--retry-connrefused",
            "--random-wait",
            "-O",
            str(fpath),
            "-c",
            url,
        ],
        check=True,
    )


class ProgressReporter:
    def __init__(self, writter):
        self._current_size = 0
        self.width = 60
        self._last_line = None
        self._writter = writter
        self.reporthook(0, 0, 100)  # display empty bar as we start

    def reporthook(self, chunk, chunk_size, total_size):
        if chunk != 0:
            self._current_size += chunk_size

        avail_dots = self.width - 2
        if total_size == -1:
            line = "unknown size"
        elif self._current_size >= total_size:
            line = "[" + "." * avail_dots + "] 100%\n"
        else:
            ratio = min(float(self._current_size) / total_size, 1.0)
            shaded_dots = min(int(ratio * avail_dots), avail_dots)
            percent = min(int(ratio * 100), 100)
            line = (
                "["
                + "." * shaded_dots
                + " " * (avail_dots - shaded_dots)
                + "] "
                + str(percent)
                + "%\r"
            )

        if line != self._last_line:
            self._last_line = line
            self._writter(line)



def save_file(
    url: str,
    fpath: pathlib.Path,
    timeout: Optional[int] = 30,
    retries: Optional[int] = 5,
) -> requests.structures.CaseInsensitiveDict:
    """download a file from its URL, and return headers
    Only recommended to be used with small files/HTMLs"""

    for left_attempts in range(retries, -1, -1):
        try:
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            with open(fpath, "wb") as fp:
                fp.write(resp.content)
            return resp.headers
        except requests.exceptions.RequestException as exc:
            logger.debug(
                f"Request for {url} failed ({left_attempts} attempts left)\n{exc}"
            )
            if left_attempts == 0:
                raise exc


def stream_file(
    url: str,
    fpath: Optional[pathlib.Path] = None,
    byte_stream: Optional[io.BytesIO] = None,
    logger_obj: Optional[Logger] = None,
    block_size: Optional[int] = 1024,
    proxies: Optional[dict] = None,
    only_first_block: Optional[bool] = False,
    max_retries: Optional[int] = 5,
) -> Union[int, requests.structures.CaseInsensitiveDict]:
    """download an URL without blocking
    - retries download on failure (with increasing wait delay)
    - writes progress information to the logger"""

    # if nothing provided
    if not fpath and not byte_stream:
        raise AttributeError("Either file path or a bytesIO object is needed")

    if logger_obj is not None:
        progress_reporter = ProgressReporter(logger.raw_std)

    # prepare adapter so it retries on failure
    session = requests.Session()
    # retries up-to FAILURE_RETRIES whichever kind of listed error
    retries = requests.packages.urllib3.util.retry.Retry(
        total=max_retries,  # total number of retries
        connect=max_retries,  # connection errors
        read=max_retries,  # read errors
        status=2,  # failure HTTP status (only those bellow)
        redirect=False,  # don't fail on redirections
        backoff_factor=30,  # sleep factor between retries
        status_forcelist=[413, 429, 500, 502, 503, 504],
    )

    retry_adapter = requests.adapters.HTTPAdapter(max_retries=retries)
    session.mount("http", retry_adapter)  # tied to http and https
    resp = session.get(
        url, stream=True, proxies=proxies,
    )

    total_size = int(resp.headers.get("content-length", 0))
    # adjust if we are only requesting first block
    if only_first_block and total_size > block_size:
        total_size = block_size

    total_downloaded = 0
    if fpath is not None:
        fp = open(fpath, "wb")
    else:
        fp = byte_stream

    for data in resp.iter_content(block_size):
        if logger_obj is not None:
            progress_reporter.reporthook(data, block_size, total_size)
        total_downloaded += len(data)
        fp.write(data)

        # stop downloading/reading if we're just testing first block
        if only_first_block:
            break

    if fpath:
        fp.close()
    else:
        fp.seek(0)
    return total_downloaded, resp.headers
