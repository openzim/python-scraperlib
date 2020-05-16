#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu


import subprocess
from . import logger
from ..logging import nicer_args_join


def reencode(src_path, dst_path, config, delete_src=False, return_output=False):
    """Runs ffmpeg with given config and returns back the returncode received from ffmpeg
    
    config - A list of ffmpeg arguments (except -threads and -max_muxing_queue_size)"""

    tmp_path = src_path.parent.joinpath(f"video.tmp{dst_path.suffix}")
    args = ["ffmpeg", "-y", "-i", f"file:{src_path}"] + config + [f"file:{tmp_path}"]
    logger.info(f"Encode {src_path} -> {dst_path} video format = {dst_path.suffix}")
    logger.debug(nicer_args_join(args))
    ffmpeg = subprocess.run(args, stderr=subprocess.PIPE, universal_newlines=True)
    if ffmpeg.returncode == 0:
        if delete_src:
            src_path.unlink()
        tmp_path.replace(dst_path)
    else:
        tmp_path.unlink(missing_ok=True)
    if return_output:
        return ffmpeg.stderr, ffmpeg.returncode
    return ffmpeg.returncode
