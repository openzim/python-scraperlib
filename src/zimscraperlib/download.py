#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import subprocess
import pathlib
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Tuple

import requests
import youtube_dl

from . import logger


class YoutubeDownloader:
    """A class to download youtube videos using youtube_dl, on a ThreadPoolExecutor
    maintaining a specified number of workers, even when executed parallely with
    a higher number of workers. The shutdown method must be run explicitly to
    free any occupied resources"""

    executor = None
    video_format = None

    def __init__(
        self, video_format: Optional[str] = "mp4", threads: Optional[int] = 2
    ) -> None:
        """Initialize the class
        Arguments:
        video_format : One of the video formats used by the scraper (used to generate youtube_dl options)
        threads: The max number of workers for the executor"""

        self.executor = ThreadPoolExecutor(max_workers=threads)
        self.video_format = video_format

    def shutdown(self) -> None:
        """ shuts down the executor """

        self.executor.shutdown(wait=True)

    def run_youtube_dl(
        self, url: str, fpath: pathlib.Path, extra_options: Optional[dict] = {}
    ) -> Tuple[bool, pathlib.Path]:
        audext, vidext = {"webm": ("webm", "webm"), "mp4": ("m4a", "mp4")}[
            self.video_format
        ]
        output_file_name = fpath.name.replace(fpath.suffix, "")
        options = {
            "outtmpl": str(fpath.parent.joinpath(f"{output_file_name}.%(ext)s")),
            "preferredcodec": self.video_format,
            "format": f"best[ext={vidext}]/bestvideo[ext={vidext}]+bestaudio[ext={audext}]/best",
            "retries": 20,
            "fragment-retries": 50,
        }
        options.update(extra_options)
        with youtube_dl.YoutubeDL(options) as ydl:
            ydl.download([url])
            for content in fpath.parent.iterdir():
                if content.is_file() and content.name.startswith(
                    f"{output_file_name}."
                ):
                    return True, content

    def download(
        self,
        video: str,
        preferred_fpath: pathlib.Path,
        extra_options: Optional[dict] = {},
    ) -> bool:
        """Downloads a video using run_youtube_dl on the initialized executor and returns whether downloaded
        and the path to the downloaded file.

        Arguments:
        video: The url/video ID of the video to download.
        preferred_path: The preferred path to save the videos to. Note that the actual
            downloaded path may be different (due to unavailability of video in certain formats)
            and the actual downloaded path is returned by the method if the download is successful
        extra_options: A dict containing any extra options that you want to pass directly to youtube_dl"""

        url = video

        # ensure url is in correct format
        if not video.startswith("https://"):
            if "youtube.com" in video or "youtu.be" in video:
                url = f"https://{video}"
            else:
                url = f"https://youtube.com/watch?v={video}"

        # run youtube_dl on the executor
        print(url)
        print(preferred_fpath)
        future = self.executor.submit(
            self.run_youtube_dl, url, preferred_fpath, extra_options
        )
        if not future.exception():
            # return the result
            return future.result()
        # raise the exception
        raise future.exception()


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
