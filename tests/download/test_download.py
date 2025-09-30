import concurrent.futures
import io
import pathlib
import re
from typing import ClassVar
from unittest.mock import Mock

import pytest
import requests
import requests.structures
from yt_dlp.utils import DownloadError

from zimscraperlib.constants import DEFAULT_WEB_REQUESTS_TIMEOUT
from zimscraperlib.download import (
    BestMp4,
    BestWebm,
    YoutubeDownloader,
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
    with pytest.raises(DownloadError, match=re.escape("is not a valid URL")):
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
