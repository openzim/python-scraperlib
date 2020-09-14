#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import subprocess
import pathlib
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Optional, Union

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
