import pathlib
import shutil
import subprocess
import tempfile
from copy import deepcopy

from zimscraperlib import logger
from zimscraperlib.filesystem import path_from
from zimscraperlib.logging import nicer_args_join


def _build_ffmpeg_args(
    src_path: pathlib.Path,
    tmp_path: pathlib.Path,
    ffmpeg_args: list[str],
    threads: int | None,
) -> list[str]:
    ffmpeg_args = deepcopy(ffmpeg_args)
    if threads:
        if "-threads" in ffmpeg_args:
            raise AttributeError("Cannot set the number of threads, already set")
        else:
            ffmpeg_args += ["-threads", str(threads)]
    args = [
        "/usr/bin/env",
        "ffmpeg",
        "-y",
        "-i",
        f"file:{src_path}",
        *ffmpeg_args,
        f"file:{tmp_path}",
    ]
    return args


def reencode(
    src_path: pathlib.Path,
    dst_path: pathlib.Path,
    ffmpeg_args: list[str],
    threads: int | None = 1,
    *,
    delete_src: bool = False,
    failsafe: bool = True,
    existing_tmp_path: pathlib.Path | None = None,
) -> tuple[bool, subprocess.CompletedProcess[str]]:
    """Runs ffmpeg with given ffmpeg_args

    Arguments -
        src_path - Path to source file
        dst_path - Path to destination file
        ffmpeg_args - A list of ffmpeg arguments
        threads - Number of encoding threads used by ffmpeg
        delete_src - Delete source file after convertion
        failsafe - Run in failsafe mode
    """

    with path_from(existing_tmp_path or tempfile.TemporaryDirectory()) as tmp_dir:

        tmp_path = pathlib.Path(tmp_dir).joinpath(f"video.tmp{dst_path.suffix}")
        args = _build_ffmpeg_args(
            src_path=src_path,
            tmp_path=tmp_path,
            ffmpeg_args=ffmpeg_args,
            threads=threads,
        )
        logger.debug(
            f"Encode {src_path} -> {dst_path} video format = {dst_path.suffix}"
        )
        logger.debug(nicer_args_join(args))
        ffmpeg = subprocess.run(
            args,
            stderr=subprocess.STDOUT,
            stdout=subprocess.PIPE,
            text=True,
            check=False,
        )
        if not failsafe:
            ffmpeg.check_returncode()
        if ffmpeg.returncode == 0:
            if delete_src:
                src_path.unlink()
            shutil.copy(tmp_path, dst_path)
        return ffmpeg.returncode == 0, ffmpeg
