import pathlib
import random
import time
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, ClassVar
from urllib.parse import urlparse

import requests
import requests.adapters
import requests.structures
import urllib3.util
import yt_dlp as youtube_dl  # pyright: ignore[reportMissingTypeStubs]

from zimscraperlib import logger
from zimscraperlib.constants import (
    DEFAULT_USER_AGENT,
    DEFAULT_WEB_REQUESTS_TIMEOUT,
    WIKIMEDIA_UPLOAD_HOST,
)
from zimscraperlib.typing import SupportsSeekableWrite, SupportsWrite


class YoutubeDownloader:
    """Download YT videos using youtube_dl on a ThreadPoolExecutor with nb_workers

    Shutdown method must be run explicitly to
    free any occupied resources"""

    def __init__(self, threads: int | None = 1) -> None:
        self.executor = ThreadPoolExecutor(max_workers=threads)

    def __enter__(self):
        return self

    def __exit__(self, *_: Any):
        self.shutdown()

    def shutdown(self) -> None:
        """shuts down the executor, awaiting completion"""
        self.executor.shutdown(wait=True)

    def _run_youtube_dl(self, url: str, options: dict[str, Any]) -> None:
        with youtube_dl.YoutubeDL(
            options  # pyright: ignore[reportArgumentType]
        ) as ydl:
            ydl.download([url])  # pyright: ignore[reportUnknownMemberType]

    def download(
        self,
        url: str,
        options: dict[str, Any] | None,
        *,
        wait: bool | None = True,
    ) -> bool | Future[Any]:
        """Downloads video using initialized executor.

        url: URL or Video ID
        options: youtube_dl options dict
        wait: whether to await download completion before returning

        Returns download result of future (wait=False)"""

        future = self.executor.submit(self._run_youtube_dl, url, options or {})
        if not wait:
            return future
        exc = future.exception()
        if isinstance(exc, BaseException):
            raise exc
        return True


class YoutubeConfig(dict[str, str | bool | int | None]):
    options: ClassVar[dict[str, str | bool | int | None]] = {}
    defaults: ClassVar[dict[str, str | bool | int | None]] = {
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

    def __init__(self, **kwargs: str | bool | int | None):
        super().__init__(self, **type(self).defaults)
        self.update(self.options)
        self.update(kwargs)

    @classmethod
    def get_options(
        cls,
        target_dir: pathlib.Path | None = None,
        filepath: pathlib.Path | None = None,
        **options: str | bool | int | None,
    ):
        if "outtmpl" not in options:
            outtmpl = cls.options.get("outtmpl", cls.defaults["outtmpl"])
            if not isinstance(outtmpl, str):
                raise ValueError(f"outtmpl must be a a str, {type(outtmpl)} found")
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
    options: ClassVar[dict[str, str | bool | int | None]] = {
        "preferredcodec": "webm",
        "format": "best[ext=webm]/bestvideo[ext=webm]+bestaudio[ext=webm]/best",
    }


class BestMp4(YoutubeConfig):
    options: ClassVar[dict[str, str | bool | int | None]] = {
        "preferredcodec": "mp4",
        "format": "best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best",
    }


HTTP_OK = 200
RETRYABLE_HTTP_STATUSES = {429, 500, 502, 503, 504}
CHUNK_SIZE = 1024 * 1024
CONNECT_TIMEOUT_SECONDS = 30
READ_TIMEOUT_SECONDS = 60
BACKOFF_BASE_SECONDS = 2
BACKOFF_MAX_SECONDS = 60


class DownloadError(Exception):
    """Raised when a download fails and cannot be retried any further."""


def save_large_file(
    url: str,
    fpath: pathlib.Path,
    retries: int = 5,
    user_agent: str | None = None,
) -> None:
    """Download a binary file from its URL, streaming the response with resume.

    Retries on connection errors, timeouts, incomplete reads, and HTTP
    429/500/502/503/504, resuming from the last byte written each time via a
    `Range` request. `retries` is the number of consecutive attempts that may
    fail *without making any progress* before giving up; an attempt that
    writes at least one byte resets this counter.
    """
    headers = {"User-Agent": user_agent} if user_agent else {}
    consecutive_failures = 0

    with requests.Session() as session:
        while True:
            resume_from = fpath.stat().st_size if fpath.exists() else 0
            request_headers = dict(headers)
            if resume_from:
                request_headers["Range"] = f"bytes={resume_from}-"

            bytes_written = 0
            error: Exception | None = None
            try:
                with session.get(
                    url,
                    headers=request_headers,
                    stream=True,
                    timeout=(CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS),
                ) as response:
                    if resume_from and response.status_code == HTTP_OK:
                        logger.warning(
                            f"{url} does not support resuming downloads, "
                            "restarting from scratch"
                        )
                        fpath.unlink(missing_ok=True)
                        resume_from = 0

                    response.raise_for_status()

                    mode = "ab" if resume_from else "wb"
                    with fpath.open(mode) as fh:
                        for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                            if not chunk:
                                continue
                            fh.write(chunk)
                            bytes_written += len(chunk)
                return  # response body was fully consumed without error
            except (
                requests.ConnectionError,
                requests.Timeout,
                requests.exceptions.ChunkedEncodingError,
            ) as exc:
                error = exc
            except requests.HTTPError as exc:
                status = exc.response.status_code if exc.response is not None else None
                if status not in RETRYABLE_HTTP_STATUSES:
                    raise DownloadError(
                        f"Download of {url} failed with non-retryable error"
                    ) from exc
                error = exc

            if bytes_written:
                consecutive_failures = 0
            else:
                consecutive_failures += 1

            if consecutive_failures > retries:
                raise DownloadError(
                    f"Download of {url} failed after {retries} consecutive "
                    "attempts without progress"
                ) from error

            wait = min(
                BACKOFF_MAX_SECONDS,
                BACKOFF_BASE_SECONDS * 2 ** (consecutive_failures - 1),
            )
            wait += random.uniform(0, wait * 0.1)  # noqa: S311
            logger.warning(
                f"Download of {url} interrupted ({error}), retrying in "
                f"{wait:.1f}s from byte {resume_from}"
            )
            time.sleep(wait)


def get_retry_adapter(
    max_retries: int | None = 5,
) -> requests.adapters.BaseAdapter:
    """A requests adapter to automatically retry on known HTTP status that can be"""
    retries = urllib3.util.retry.Retry(
        total=max_retries,  # total number of retries
        connect=max_retries,  # connection errors
        read=max_retries,  # read errors
        status=2,  # failure HTTP status (only those bellow)
        redirect=False,  # don't fail on redirections
        backoff_factor=30,  # sleep factor between retries
        status_forcelist=[
            413,
            429,
            500,
            502,
            503,
            504,
        ],  # force retry on the following codes
    )

    return requests.adapters.HTTPAdapter(max_retries=retries)


def get_session(max_retries: int | None = 5) -> requests.Session:
    """Session to hold cookies and connection pool together"""
    session = requests.Session()
    session.mount("http", get_retry_adapter(max_retries))  # tied to http and https
    return session


def is_wikimedia_upload_url(url: str) -> bool:
    """Whether the URL points to a file hosted on Wikimedia upload servers"""
    return (urlparse(url).hostname or "").lower() == WIKIMEDIA_UPLOAD_HOST


def has_user_agent_header(headers: dict[str, str] | None) -> bool:
    """Whether a User-Agent header is already set, whatever its casing"""
    return any(key.lower() == "user-agent" for key in (headers or {}))


def stream_file(  # noqa: PLR0917
    url: str,
    fpath: pathlib.Path | None = None,
    byte_stream: SupportsWrite[bytes] | SupportsSeekableWrite[bytes] | None = None,
    block_size: int | None = 1024,
    proxies: dict[str, str] | None = None,
    max_retries: int | None = 5,
    headers: dict[str, str] | None = None,
    session: requests.Session | None = None,
    timeout: int | None = DEFAULT_WEB_REQUESTS_TIMEOUT,
    *,
    only_first_block: bool | None = False,
) -> tuple[int, requests.structures.CaseInsensitiveDict[str]]:
    """Stream data from a URL to either a BytesIO object or a file
    Arguments -
        fpath - Path of the file where data is sent
        byte_stream - The BytesIO object where data is sent
        block_size - Size of each chunk of data read in one iteration
        proxies - A dict of proxies to be used
        https://requests.readthedocs.io/en/master/user/advanced/#proxies
        only_first_block - Whether to download only one (first) block
        max_retries - Maximum number of retries after which error is raised. Does not
        apply if using your own session
        session - Session object to make the request with. A new one created otherwise
    Returns the total number of bytes downloaded and the response headers"""

    # if no output option is supplied
    if fpath is None and byte_stream is None:
        raise ValueError("Either file path or a bytesIO object is needed")

    if not session:
        session = get_session(max_retries)

    if is_wikimedia_upload_url(url) and not has_user_agent_header(headers):
        headers = {**(headers or {}), "User-Agent": DEFAULT_USER_AGENT}

    resp = session.get(
        url,
        stream=True,
        proxies=proxies,
        headers=headers,
        timeout=timeout,
    )
    resp.raise_for_status()

    total_downloaded = 0
    if fpath is not None:
        fpath_handler = open(fpath, "wb")
    else:
        fpath_handler = None

    for data in resp.iter_content(block_size):
        total_downloaded += len(data)
        if fpath_handler:
            fpath_handler.write(data)
        if byte_stream:
            byte_stream.write(data)

        # stop downloading/reading if we're just testing first block
        if only_first_block:
            break

    logger.debug(f"Downloaded {total_downloaded} bytes from {url}")

    if fpath_handler:
        fpath_handler.close()
    elif isinstance(byte_stream, SupportsSeekableWrite) and byte_stream.seekable():
        byte_stream.seek(0)
    return total_downloaded, resp.headers
