import pathlib

import pytest


@pytest.fixture(scope="function")
def test_files() -> dict[str, pathlib.Path]:
    files_dir = pathlib.Path(__file__).parent.parent.joinpath("files")
    return {
        "mp4": files_dir.joinpath("video.mp4"),
        "mkv": files_dir.joinpath("video.mkv"),
        "webm": files_dir.joinpath("video.webm"),
        "mp3": files_dir.joinpath("audio.mp3"),
    }
