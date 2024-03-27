from __future__ import annotations

import re
from copy import deepcopy
from pathlib import Path

import pytest

from zimscraperlib.video.encoding import _build_ffmpeg_args
from zimscraperlib.video.presets import VideoWebmLow


@pytest.mark.parametrize(
    "src_path,tmp_path,ffmpeg_args,threads,expected",
    [
        (
            Path("path1/file1.mp4"),
            Path("path1/fileout.mp4"),
            [
                "-codec:v",
                "libx265",
            ],
            None,
            [
                "/usr/bin/env",
                "ffmpeg",
                "-y",
                "-i",
                "file:path1/file1.mp4",
                "-codec:v",
                "libx265",
                "file:path1/fileout.mp4",
            ],
        ),
        (
            Path("path2/file2.mp4"),
            Path("path12/tmpfile.mp4"),
            [
                "-b:v",
                "300k",
            ],
            1,
            [
                "/usr/bin/env",
                "ffmpeg",
                "-y",
                "-i",
                "file:path2/file2.mp4",
                "-b:v",
                "300k",
                "-threads",
                "1",
                "file:path12/tmpfile.mp4",
            ],
        ),
        (
            Path("path2/file2.mp4"),
            Path("path12/tmpfile.mp4"),
            [
                "-b:v",
                "300k",
                "-threads",
                "1",
            ],
            1,
            None,
        ),
    ],
)
def test_build_ffmpeg_args(
    src_path: Path,
    tmp_path: Path,
    ffmpeg_args: list[str],
    threads: int | None,
    expected: list[str] | None,
):
    if expected:
        assert (
            _build_ffmpeg_args(
                src_path=src_path,
                tmp_path=tmp_path,
                ffmpeg_args=ffmpeg_args,
                threads=threads,
            )
            == expected
        )
    else:
        with pytest.raises(
            AttributeError,
            match=re.escape("Cannot set the number of threads, already set"),
        ):
            _build_ffmpeg_args(
                src_path=src_path,
                tmp_path=tmp_path,
                ffmpeg_args=ffmpeg_args,
                threads=threads,
            )


def test_ffmpeg_args_not_modified():
    """_build_ffmpeg_args hould not alter the original ffmpeg_args"""
    preset = VideoWebmLow()
    ffmpeg_args = preset.to_ffmpeg_args()
    ffmpeg_args_orig = deepcopy(ffmpeg_args)
    src_path = Path("file1.mp4")
    tmp_path = Path("file2.mp4")

    _build_ffmpeg_args(
        src_path=src_path, tmp_path=tmp_path, ffmpeg_args=ffmpeg_args, threads=1
    )
    assert ffmpeg_args == ffmpeg_args_orig
