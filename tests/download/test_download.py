import concurrent.futures
import io
import pathlib
import re
from collections.abc import Iterator
from typing import ClassVar
from unittest.mock import MagicMock, Mock

import pytest
import requests
import requests.structures
from yt_dlp.utils import DownloadError as YtDlpDownloadError

from zimscraperlib.constants import DEFAULT_USER_AGENT, DEFAULT_WEB_REQUESTS_TIMEOUT
from zimscraperlib.download import (
    BestMp4,
    BestWebm,
    DownloadError,
    YoutubeDownloader,
    _format_size,  # pyright: ignore[reportPrivateUsage]
    has_user_agent_header,
    is_wikimedia_upload_url,
    save_large_file,
    stream_file,
)


def assert_downloaded_file(url: str, file: pathlib.Path):
    assert file.exists()
    # our google test urls dont support HEAD
    req = requests.get(url, timeout=DEFAULT_WEB_REQUESTS_TIMEOUT)
    # we test against binary response: Content-Length not accurate as gzip-encoded
    assert file.stat().st_size == len(req.content)


def assert_headers(returned_headers: requests.structures.CaseInsensitiveDict[str]):
    assert isinstance(returned_headers, requests.structures.CaseInsensitiveDict)
    assert returned_headers["Content-Type"] == "image/x-icon"


def get_dest_file(tmp_path: pathlib.Path):
    return tmp_path.joinpath("favicon.ico")


def test_missing_dest():
    with pytest.raises(requests.exceptions.ConnectionError):
        stream_file(url="http://some_url", byte_stream=io.BytesIO())


def test_invalid_url(tmp_path: pathlib.Path, invalid_url: str):
    dest_file = tmp_path / "favicon.ico"
    with pytest.raises(requests.exceptions.ConnectionError):
        stream_file(url=invalid_url, fpath=dest_file)


def test_no_output_supplied(valid_http_url: str):
    with pytest.raises(
        ValueError, match="Either file path or a bytesIO object is needed"
    ):
        stream_file(url=valid_http_url)


def test_first_block_download_default_session(valid_http_url: str):
    byte_stream = io.BytesIO()
    _, ret = stream_file(
        url=valid_http_url, byte_stream=byte_stream, only_first_block=True
    )
    assert_headers(ret)
    # valid_http_url randomly returns gzip-encoded content.
    # otherwise, expected size is default block size
    expected = 3062 if ret.get("Content-Encoding") == "gzip" else 1024
    assert len(byte_stream.read()) <= expected


def test_filehandler(tmp_path: pathlib.Path, valid_http_url: str):
    dest_file = pathlib.Path(tmp_path / "favicon.ico")

    def notseekable():
        return False

    with open(dest_file, "wb") as byte_stream:
        assert byte_stream.seekable()
        _, ret = stream_file(
            url=valid_http_url, byte_stream=byte_stream, only_first_block=True
        )
        assert_headers(ret)
        assert byte_stream.tell() == 0

        byte_stream.seekable = notseekable
        assert not byte_stream.seekable()
        _, ret = stream_file(
            url=valid_http_url, byte_stream=byte_stream, only_first_block=True
        )
        assert_headers(ret)
        assert byte_stream.tell() > 0


def test_first_block_download_custom_session(mocker: Mock, valid_http_url: str):
    byte_stream = io.BytesIO()
    custom_session = mocker.Mock(spec=requests.Session)

    expected_response = requests.Response()
    expected_response.status_code = 200
    expected_response.raw = io.BytesIO(b"Whatever\n")
    custom_session.get.return_value = expected_response

    mocker.patch("requests.Session")
    stream_file(
        url=valid_http_url,
        byte_stream=byte_stream,
        only_first_block=True,
        session=custom_session,
    )
    # check that custom session has been used
    custom_session.get.assert_called_once_with(
        valid_http_url,
        stream=True,
        proxies=None,
        headers=None,
        timeout=DEFAULT_WEB_REQUESTS_TIMEOUT,
    )
    requests.Session.assert_not_called()  # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType]


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://upload.wikimedia.org/wikipedia/commons/4/4a/Commons-logo.svg", True),
        ("http://upload.wikimedia.org/wikipedia/commons/a/b.png", True),
        ("https://UPLOAD.WIKIMEDIA.ORG/wikipedia/commons/a/b.png", True),
        ("https://commons.wikimedia.org/wiki/File:Commons-logo.svg", False),
        ("https://wikimedia.org/", False),
        ("https://example.com/favicon.ico", False),
        ("not-an-url", False),
    ],
)
def test_is_wikimedia_upload_url(url: str, *, expected: bool):
    assert is_wikimedia_upload_url(url) is expected


@pytest.mark.parametrize(
    "headers,expected",
    [
        (None, False),
        ({}, False),
        ({"Accept": "image/png"}, False),
        ({"User-Agent": "zimscraperlib-test"}, True),
        ({"user-agent": "zimscraperlib-test"}, True),
    ],
)
def test_has_user_agent_header(headers: dict[str, str] | None, *, expected: bool):
    assert has_user_agent_header(headers) is expected


@pytest.mark.parametrize(
    "headers",
    [None, {}, {"Accept": "image/png"}],
)
def test_wikimedia_upload_default_user_agent(
    mocker: Mock, headers: dict[str, str] | None
):
    url = "https://upload.wikimedia.org/wikipedia/commons/4/4a/Commons-logo.svg"
    byte_stream = io.BytesIO()
    custom_session = mocker.Mock(spec=requests.Session)

    expected_response = requests.Response()
    expected_response.status_code = 200
    expected_response.raw = io.BytesIO(b"Whatever\n")
    custom_session.get.return_value = expected_response

    mocker.patch("requests.Session")
    stream_file(
        url=url,
        byte_stream=byte_stream,
        headers=headers,
        only_first_block=True,
        session=custom_session,
    )
    custom_session.get.assert_called_once_with(
        url,
        stream=True,
        proxies=None,
        headers={**(headers or {}), "User-Agent": DEFAULT_USER_AGENT},
        timeout=DEFAULT_WEB_REQUESTS_TIMEOUT,
    )
    requests.Session.assert_not_called()  # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType]


def test_wikimedia_upload_custom_user_agent(mocker: Mock):
    url = "https://upload.wikimedia.org/wikipedia/commons/4/4a/Commons-logo.svg"
    byte_stream = io.BytesIO()
    custom_session = mocker.Mock(spec=requests.Session)

    expected_response = requests.Response()
    expected_response.status_code = 200
    expected_response.raw = io.BytesIO(b"Whatever\n")
    custom_session.get.return_value = expected_response

    mocker.patch("requests.Session")
    stream_file(
        url=url,
        byte_stream=byte_stream,
        headers={"User-Agent": "myscraper/1.0 (me@example.org)"},
        only_first_block=True,
        session=custom_session,
    )
    custom_session.get.assert_called_once_with(
        url,
        stream=True,
        proxies=None,
        headers={"User-Agent": "myscraper/1.0 (me@example.org)"},
        timeout=DEFAULT_WEB_REQUESTS_TIMEOUT,
    )
    requests.Session.assert_not_called()  # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType]


@pytest.mark.slow
def test_user_agent():
    ua = "zimscraperlib-test"
    byte_stream = io.BytesIO()
    stream_file(
        url="http://useragent.fr/",
        byte_stream=byte_stream,
        headers={"User-Agent": "zimscraperlib-test"},
    )
    assert ua in byte_stream.read().decode("utf-8")


@pytest.mark.slow
def test_save_http(tmp_path: pathlib.Path, valid_http_url: str):
    dest_file = tmp_path / "favicon.ico"
    _, ret = stream_file(url=valid_http_url, fpath=dest_file)
    assert_headers(ret)
    assert_downloaded_file(valid_http_url, dest_file)


@pytest.mark.slow
def test_save_https(tmp_path: pathlib.Path, valid_https_url: str):
    dest_file = tmp_path / "favicon.ico"
    _, ret = stream_file(url=valid_https_url, fpath=dest_file)
    assert_headers(ret)
    assert_downloaded_file(valid_https_url, dest_file)


@pytest.mark.slow
def test_stream_to_bytes(valid_https_url: str):
    byte_stream = io.BytesIO()
    _, ret = stream_file(url=valid_https_url, byte_stream=byte_stream)
    assert_headers(ret)
    assert (
        byte_stream.read()
        == requests.get(valid_https_url, timeout=DEFAULT_WEB_REQUESTS_TIMEOUT).content
    )


@pytest.mark.slow
def test_unseekable_stream(valid_https_url: str):
    def notseekable():
        return False

    byte_stream = io.BytesIO()
    byte_stream.seekable = notseekable
    _, ret = stream_file(url=valid_https_url, byte_stream=byte_stream)
    assert_headers(ret)


@pytest.mark.slow
def test_save_parent_folder_missing(tmp_path: pathlib.Path, valid_http_url: str):
    dest_file = tmp_path / "some-folder" / "favicon.ico"
    with pytest.raises(IOError):
        stream_file(url=valid_http_url, fpath=dest_file)


@pytest.mark.slow
def test_save_http_error(tmp_path: pathlib.Path, http_error_url: str):
    dest_file = tmp_path / "favicon.ico"
    with pytest.raises(requests.exceptions.HTTPError):
        stream_file(url=http_error_url, fpath=dest_file)


@pytest.mark.slow
def test_large_download_http(tmp_path: pathlib.Path, valid_http_url: str):
    dest_file = tmp_path / "favicon.ico"
    save_large_file(valid_http_url, dest_file)
    assert_downloaded_file(valid_http_url, dest_file)


@pytest.mark.slow
def test_large_download_https(tmp_path: pathlib.Path, valid_https_url: str):
    dest_file = tmp_path / "favicon.ico"
    save_large_file(valid_https_url, dest_file)
    assert_downloaded_file(valid_https_url, dest_file)


@pytest.mark.slow
def test_large_download_https_custom_retry(
    tmp_path: pathlib.Path, valid_https_url: str
):
    dest_file = tmp_path / "favicon.ico"
    save_large_file(valid_https_url, dest_file, 1)
    assert_downloaded_file(valid_https_url, dest_file)


@pytest.mark.slow
def test_large_download_https_custom_ua(tmp_path: pathlib.Path, valid_https_url: str):
    dest_file = tmp_path / "favicon.ico"
    save_large_file(
        valid_https_url,
        dest_file,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36",
    )
    assert_downloaded_file(valid_https_url, dest_file)


class FakeResponse:
    """Minimal stand-in for requests.Response, usable as a context manager."""

    def __init__(
        self,
        status_code: int,
        chunks: list[bytes] | None = None,
        raise_while_streaming: Exception | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self._chunks = chunks or []
        self._raise_while_streaming = raise_while_streaming
        self.headers = headers or {}

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            response = requests.Response()
            response.status_code = self.status_code
            raise requests.HTTPError(response=response)

    def iter_content(self, _chunk_size: int) -> Iterator[bytes]:
        yield from self._chunks
        if self._raise_while_streaming:
            raise self._raise_while_streaming


def test_save_large_file_single_attempt(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A clean download writes all chunks in one attempt, without a Range header."""
    get_mock = MagicMock(return_value=FakeResponse(200, [b"hello ", b"", b"world"]))
    monkeypatch.setattr(requests.Session, "get", get_mock)

    fpath = tmp_path / "out.zim"
    save_large_file("https://example.com/file.zim", fpath, user_agent="some-agent")

    assert fpath.read_bytes() == b"hello world"
    _args, kwargs = get_mock.call_args
    assert kwargs["headers"] == {"User-Agent": "some-agent"}
    assert "Range" not in kwargs["headers"]


def test_save_large_file_without_user_agent(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    get_mock = MagicMock(return_value=FakeResponse(200, [b"data"]))
    monkeypatch.setattr(requests.Session, "get", get_mock)

    fpath = tmp_path / "out.zim"
    save_large_file("https://example.com/file.zim", fpath)

    _args, kwargs = get_mock.call_args
    assert "User-Agent" not in kwargs["headers"]


def test_save_large_file_default_user_agent_for_wikimedia(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    get_mock = MagicMock(return_value=FakeResponse(200, [b"data"]))
    monkeypatch.setattr(requests.Session, "get", get_mock)

    fpath = tmp_path / "out.zim"
    save_large_file(
        "https://upload.wikimedia.org/wikipedia/commons/4/4a/Commons-logo.svg",
        fpath,
    )

    _args, kwargs = get_mock.call_args
    assert kwargs["headers"]["User-Agent"] == DEFAULT_USER_AGENT


def test_save_large_file_accepts_arbitrary_headers(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    get_mock = MagicMock(return_value=FakeResponse(200, [b"data"]))
    monkeypatch.setattr(requests.Session, "get", get_mock)

    fpath = tmp_path / "out.zim"
    save_large_file(
        "https://example.com/file.zim", fpath, headers={"Accept": "image/png"}
    )

    _args, kwargs = get_mock.call_args
    assert kwargs["headers"]["Accept"] == "image/png"
    assert "User-Agent" not in kwargs["headers"]


def test_save_large_file_user_agent_overrides_header(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    get_mock = MagicMock(return_value=FakeResponse(200, [b"data"]))
    monkeypatch.setattr(requests.Session, "get", get_mock)

    fpath = tmp_path / "out.zim"
    save_large_file(
        "https://example.com/file.zim",
        fpath,
        user_agent="custom-agent",
        headers={"user-agent": "header-agent", "Accept": "image/png"},
    )

    _args, kwargs = get_mock.call_args
    assert kwargs["headers"] == {
        "Accept": "image/png",
        "User-Agent": "custom-agent",
    }


def test_save_large_file_keeps_header_user_agent_for_wikimedia(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    get_mock = MagicMock(return_value=FakeResponse(200, [b"data"]))
    monkeypatch.setattr(requests.Session, "get", get_mock)

    fpath = tmp_path / "out.zim"
    save_large_file(
        "https://upload.wikimedia.org/wikipedia/commons/4/4a/Commons-logo.svg",
        fpath,
        headers={"User-Agent": "header-agent"},
    )

    _args, kwargs = get_mock.call_args
    assert kwargs["headers"]["User-Agent"] == "header-agent"


def test_save_large_file_default_user_agent_for_wikimedia_with_other_headers(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    get_mock = MagicMock(return_value=FakeResponse(200, [b"data"]))
    monkeypatch.setattr(requests.Session, "get", get_mock)

    fpath = tmp_path / "out.zim"
    save_large_file(
        "https://upload.wikimedia.org/wikipedia/commons/4/4a/Commons-logo.svg",
        fpath,
        headers={"Accept": "image/png"},
    )

    _args, kwargs = get_mock.call_args
    assert kwargs["headers"] == {
        "Accept": "image/png",
        "User-Agent": DEFAULT_USER_AGENT,
    }


def test_save_large_file_resumes_after_connection_error(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A dropped connection resumes with a Range header for the missing bytes."""
    responses = [
        FakeResponse(
            200,
            [b"hello "],
            raise_while_streaming=requests.ConnectionError("dropped"),
        ),
        FakeResponse(206, [b"world"]),
    ]
    get_mock = MagicMock(side_effect=responses)
    monkeypatch.setattr(requests.Session, "get", get_mock)
    monkeypatch.setattr("zimscraperlib.download.time.sleep", MagicMock())

    fpath = tmp_path / "out.zim"
    save_large_file("https://example.com/file.zim", fpath)

    assert fpath.read_bytes() == b"hello world"
    assert get_mock.call_count == 2
    assert get_mock.call_args_list[1].kwargs["headers"]["Range"] == "bytes=6-"


def test_save_large_file_retries_on_retryable_http_status(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    get_mock = MagicMock(side_effect=[FakeResponse(503), FakeResponse(200, [b"ok"])])
    monkeypatch.setattr(requests.Session, "get", get_mock)
    monkeypatch.setattr("zimscraperlib.download.time.sleep", MagicMock())

    fpath = tmp_path / "out.zim"
    save_large_file("https://example.com/file.zim", fpath)

    assert fpath.read_bytes() == b"ok"
    assert get_mock.call_count == 2


def test_save_large_file_restarts_when_server_ignores_range(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If the server replies 200 (not 206) to a Range request, start over."""
    fpath = tmp_path / "out.zim"
    fpath.with_name("out.zim.part").write_bytes(b"stale-partial-data")

    get_mock = MagicMock(return_value=FakeResponse(200, [b"fresh"]))
    monkeypatch.setattr(requests.Session, "get", get_mock)

    save_large_file("https://example.com/file.zim", fpath)

    assert fpath.read_bytes() == b"fresh"
    assert not fpath.with_name("out.zim.part").exists()
    assert get_mock.call_args.kwargs["headers"]["Range"] == "bytes=18-"


def test_save_large_file_does_not_retry_non_retryable_http_status(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    get_mock = MagicMock(return_value=FakeResponse(404))
    monkeypatch.setattr(requests.Session, "get", get_mock)

    fpath = tmp_path / "out.zim"
    with pytest.raises(DownloadError):
        save_large_file("https://example.com/file.zim", fpath)

    assert get_mock.call_count == 1


def test_save_large_file_gives_up_after_consecutive_failures_without_progress(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    get_mock = MagicMock(
        side_effect=requests.ConnectionError("always fails before any byte")
    )
    monkeypatch.setattr(requests.Session, "get", get_mock)
    monkeypatch.setattr("zimscraperlib.download.time.sleep", MagicMock())

    fpath = tmp_path / "out.zim"
    with pytest.raises(DownloadError):
        save_large_file("https://example.com/file.zim", fpath, retries=2)

    assert get_mock.call_count == 3


def test_save_large_file_keeps_retrying_as_long_as_progress_is_made(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every attempt but the last writes a byte before failing; progress keeps
    resetting the failure counter, so more than `retries` attempts in a row are
    allowed as long as each one makes progress."""
    failing_responses = [
        FakeResponse(
            200 if index == 0 else 206,
            [b"x"],
            raise_while_streaming=requests.ConnectionError("dropped"),
        )
        for index in range(4)
    ]
    get_mock = MagicMock(side_effect=[*failing_responses, FakeResponse(206, [b"x"])])
    monkeypatch.setattr(requests.Session, "get", get_mock)
    monkeypatch.setattr("zimscraperlib.download.time.sleep", MagicMock())

    fpath = tmp_path / "out.zim"
    save_large_file("https://example.com/file.zim", fpath, retries=2)

    assert fpath.read_bytes() == b"xxxxx"
    assert get_mock.call_count == 5


def test_save_large_file_leaves_no_part_file_on_success(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        requests.Session, "get", MagicMock(return_value=FakeResponse(200, [b"data"]))
    )

    fpath = tmp_path / "out.zim"
    save_large_file("https://example.com/file.zim", fpath)

    assert fpath.read_bytes() == b"data"
    assert not fpath.with_name("out.zim.part").exists()


def test_save_large_file_reports_progress_with_total_size(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Progress is reported once the interval elapses, with the total size known."""
    monkeypatch.setattr("zimscraperlib.download._DOWNLOAD_PROGRESS_INTERVAL", 0)
    monkeypatch.setattr(
        requests.Session,
        "get",
        MagicMock(
            return_value=FakeResponse(
                200,
                [b"hello ", b"world"],
                headers={"Content-Length": "11"},
            )
        ),
    )
    progress: list[tuple[int, int | None]] = []

    fpath = tmp_path / "out.zim"
    save_large_file(
        "https://example.com/file.zim",
        fpath,
        on_progress=lambda downloaded, total: progress.append((downloaded, total)),
    )

    assert fpath.read_bytes() == b"hello world"
    assert progress == [(6, 11), (11, 11)]


def test_save_large_file_reports_progress_without_total_size(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without a Content-Length header, progress is reported with an unknown total."""
    monkeypatch.setattr("zimscraperlib.download._DOWNLOAD_PROGRESS_INTERVAL", 0)
    monkeypatch.setattr(
        requests.Session, "get", MagicMock(return_value=FakeResponse(200, [b"data"]))
    )

    fpath = tmp_path / "out.zim"
    save_large_file("https://example.com/file.zim", fpath)

    assert fpath.read_bytes() == b"data"


@pytest.mark.parametrize(
    "num_bytes,expected",
    [
        (0, "0 B"),
        (500, "500 B"),
        (1536, "1.5 KiB"),
        (1024 * 1024, "1.0 MiB"),
        (1024**4, "1.0 TiB"),
    ],
)
def test_format_size(num_bytes: int, expected: str) -> None:
    assert _format_size(num_bytes) == expected


@pytest.mark.slow
@pytest.mark.parametrize(
    "url,video_id",
    [
        ("https://tube.jeena.net/w/tyekuoPZqb7BtkyNPwVHJL", "tyekuoPZqb7BtkyNPwVHJL"),
        ("https://tube.jeena.net/w/tyekuoPZqb7BtkyNPwVHJL", "tyekuoPZqb7BtkyNPwVHJL"),
    ],
)
def test_youtube_download_serial(url: str, video_id: str, tmp_path: pathlib.Path):
    yt_downloader = YoutubeDownloader(threads=1)
    options = BestMp4.get_options(
        target_dir=tmp_path,
        filepath=pathlib.Path("%(id)s/video.%(ext)s"),
    )
    yt_downloader.download(url, options)
    assert tmp_path.joinpath(video_id).joinpath("video.mp4").exists()
    yt_downloader.shutdown()


@pytest.mark.slow
def test_youtube_download_nowait(tmp_path: pathlib.Path):
    with YoutubeDownloader(threads=1) as yt_downloader:
        future = yt_downloader.download(
            "https://tube.jeena.net/w/tyekuoPZqb7BtkyNPwVHJL",
            BestMp4.get_options(target_dir=tmp_path),
            wait=False,
        )
        assert isinstance(future, concurrent.futures.Future)
        assert future.running()
        assert not yt_downloader.executor._shutdown
        done, not_done = concurrent.futures.wait(
            [future],
            return_when=concurrent.futures.ALL_COMPLETED,
        )
        assert future.exception() is None
        assert len(done) == 1
        assert len(not_done) == 0


@pytest.mark.slow
def test_youtube_download_error():
    yt_downloader = YoutubeDownloader(threads=1)
    with pytest.raises(YtDlpDownloadError, match=re.escape("is not a valid URL")):
        yt_downloader.download("11", BestMp4.get_options())
    yt_downloader.shutdown()


@pytest.mark.slow
def test_youtube_download_contextmanager(tmp_path: pathlib.Path):
    with YoutubeDownloader(threads=1) as yt_downloader:
        yt_downloader.download(
            "https://tube.jeena.net/w/tyekuoPZqb7BtkyNPwVHJL",
            BestWebm.get_options(target_dir=tmp_path),
        )
    assert yt_downloader.executor._shutdown
    assert tmp_path.joinpath("video.mp4").exists()  # jeena doesn't offer webm


@pytest.fixture
def target_dir() -> pathlib.Path:
    return pathlib.Path("adir1")


@pytest.fixture
def filepath() -> pathlib.Path:
    return pathlib.Path("adir2/afile")


@pytest.fixture
def custom_outtmpl() -> str:
    return "custom.%(ext)s"


class WrongOuttmplType(BestWebm):
    options: ClassVar[dict[str, str | bool | int | None]] = {"outtmpl": 123}


def test_get_options_wrong_outtmpl_type():
    with pytest.raises(ValueError):
        WrongOuttmplType.get_options()


def test_get_options_target_dir(target_dir: pathlib.Path):
    options = BestWebm.get_options(target_dir=target_dir)
    assert options["outtmpl"] == "adir1/video.%(ext)s"


def test_get_options_filepath(filepath: pathlib.Path):
    options = BestWebm.get_options(filepath=filepath)
    assert options["outtmpl"] == "adir2/afile"


def test_get_options_target_dir_filepath(
    target_dir: pathlib.Path, filepath: pathlib.Path
):
    options = BestWebm.get_options(target_dir=target_dir, filepath=filepath)
    assert options["outtmpl"] == "adir1/adir2/afile"


def test_get_options_override_outtmpl_no_other_vars(custom_outtmpl: str):
    original = BestWebm.get_options()
    overriden = BestWebm.get_options(outtmpl=custom_outtmpl)
    assert "outtmpl" in original
    assert "outtmpl" in overriden
    for key, value in original.items():
        if key != "outtmpl":
            assert overriden[key] == value
        else:
            assert overriden[key] == custom_outtmpl


def test_get_options_override_outtmpl_other_vars(
    target_dir: pathlib.Path, filepath: pathlib.Path, custom_outtmpl: str
):
    original = BestWebm.get_options(target_dir=target_dir, filepath=filepath)
    overriden = BestWebm.get_options(
        target_dir=target_dir,
        filepath=filepath,
        outtmpl=custom_outtmpl,
    )
    assert "outtmpl" in original
    assert "outtmpl" in overriden
    for key, value in original.items():
        if key != "outtmpl":
            assert overriden[key] == value
        else:
            assert overriden[key] == custom_outtmpl
