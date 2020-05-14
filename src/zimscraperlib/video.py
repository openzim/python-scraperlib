#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import subprocess

from . import logger
from .logging import nicer_args_join


class ConfigBuilder(object):
    def __init__(
        self,
        video_codec="h264",
        audio_codec="aac",
        max_video_bitrate="300k",
        min_video_bitrate=None,
        target_video_bitrate="300k",
        buffersize="1000k",
        audio_sampling_rate=44100,
        target_audio_bitrate="128k",
        quantizer_scale_range=(30, 42),
        video_scale="480:trunc(ow/a/2)*2",
        extra_params=["-movflags", "+faststart"],
    ):
        self.video_codec = video_codec
        self.audio_codec = audio_codec
        self.max_video_bitrate = max_video_bitrate
        self.min_video_bitrate = min_video_bitrate
        self.target_video_bitrate = target_video_bitrate
        self.buffersize = buffersize
        self.audio_sampling_rate = audio_sampling_rate
        self.target_audio_bitrate = target_audio_bitrate
        self.quantizer_scale_range = quantizer_scale_range
        self.video_scale = video_scale
        self.extra_params = extra_params

    def update(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def to_ffmpeg_args(self):
        arg_list = []
        # video options
        if self.video_codec:
            arg_list += ["-codec:v", self.video_codec]
            if self.target_video_bitrate:
                arg_list += ["-b:v", self.target_video_bitrate]
            if self.min_video_bitrate:
                arg_list += ["-minrate", str(self.min_video_bitrate)]
            if self.max_video_bitrate:
                arg_list = ["-maxrate", self.max_video_bitrate]
            if self.buffersize:
                arg_list = ["-bufsize", self.buffersize]
            if self.quantizer_scale_range:
                qmin, qmax = self.quantizer_scale_range
                if qmin < -1 or qmin > 69 or qmax < -1 or qmax > 1024:
                    raise ValueError(
                        "Quantizer scale must range from (-1, -1) to (69, 1024)"
                    )
                else:
                    arg_list += ["-qmin", str(qmin), "-qmax", str(qmax)]
            if self.video_scale:
                arg_list += ["-vf", f"scale='{self.video_scale}'"]

        # audio options
        if self.audio_codec:
            arg_list += [
                "-codec:a",
                self.audio_codec,
                "-ar",
                str(self.audio_sampling_rate),
                "-b:a",
                self.target_audio_bitrate,
            ]

        # extra options
        if self.extra_params:
            arg_list += self.extra_params
        return arg_list


def reencode(
    src_path,
    dst_path,
    config,
    delete_src=True,
    threads=None,
    max_muxing_queue_size=9999,
):
    tmp_path = src_path.parent.joinpath(f"video.tmp{dst_path.suffix}")
    args = ["ffmpeg", "-y", "-i", f"file:{src_path}"] + config
    if threads:
        args += ["-threads", str(threads)]
    if max_muxing_queue_size:
        args += ["-max_muxing_queue_size", str(max_muxing_queue_size)]
    args += [f"file:{tmp_path}"]
    logger.info(f"Encode {src_path} -> {dst_path} video format = {dst_path.suffix}")
    logger.debug(nicer_args_join(args))
    subprocess.run(args, check=True)
    if delete_src:
        src_path.unlink()
    tmp_path.replace(dst_path)


def get_media_info(src_path):
    args = [
        "ffprobe",
        "-i",
        f"file:{src_path}",
        "-show_entries",
        "stream=codec_name",
        "-show_entries",
        "format=duration,bit_rate",
        "-v",
        "quiet",
        "-of",
        "csv",
    ]
    print(" ".join(args))
    ffprobe = subprocess.run(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        check=False,
    )
    ffprobe_result = ffprobe.stdout.strip().split("\n")
    streams = ffprobe_result[:-1]
    codecs = [stream.split(",")[-1] for stream in streams]
    format_info = ffprobe_result[-1].split(",")[1:]
    return {
        "codecs": codecs,
        "duration": int(format_info[0].split(".")[0]),
        "bitrate": int(format_info[1]),
    }
