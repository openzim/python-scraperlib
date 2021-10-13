#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu


import pathlib
import shutil
import subprocess
import tempfile

from .. import logger
from ..logging import nicer_args_join


def reencode(
    src_path, dst_path, ffmpeg_args, delete_src=False, with_process=False, failsafe=True
):
    """Runs ffmpeg with given ffmpeg_args

    Arguments -
        src_path - Path to source file
        dst_path - Path to destination file
        ffmpeg_args - A list of ffmpeg arguments
        delete_src - Delete source file after convertion
        with_process - Optionally return the output from ffmpeg (stderr and stdout)
        failsafe - Run in failsafe mode
    """

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = pathlib.Path(tmp_dir).joinpath(f"video.tmp{dst_path.suffix}")
        args = (
            ["ffmpeg", "-y", "-i", f"file:{src_path}"]
            + ffmpeg_args
            + [f"file:{tmp_path}"]
        )
        logger.debug(
            f"Encode {src_path} -> {dst_path} " f"video format = {dst_path.suffix}"
        )
        logger.debug(nicer_args_join(args))
        ffmpeg = subprocess.run(
            args,
            stderr=subprocess.STDOUT,
            stdout=subprocess.PIPE,
            universal_newlines=True,
        )
        if not failsafe:
            ffmpeg.check_returncode()
        if ffmpeg.returncode == 0:
            if delete_src:
                src_path.unlink()
            shutil.copy(tmp_path, dst_path)
        if with_process:
            return ffmpeg.returncode == 0, ffmpeg
        return ffmpeg.returncode == 0
