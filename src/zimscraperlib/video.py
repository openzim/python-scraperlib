#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import subprocess

from . import logger
from .logging import nicer_args_join


class VidCompressionConfig(object):
    video_codecs = {"mp4": "h264", "webm": "libvpx"}
    audio_codecs = {"mp4": "aac", "webm": "libvorbis"}
    params = {"mp4": ["-movflags", "+faststart"], "webm": []}

    def __init__(
        self,
        video_format,
        max_video_bitrate="300k",
        min_video_bitrate=None,
        target_video_bitrate="300k",
        buffersize="1000k",
        audio_sampling_rate=44100,
        target_audio_bitrate="128k",
        quality_range=(30, 42),
        ffmpeg_video_scale="480:trunc(ow/a/2)*2",
    ):
        self.video_format = video_format
        self.max_video_bitrate = max_video_bitrate
        self.min_video_bitrate = min_video_bitrate
        self.target_video_bitrate = target_video_bitrate
        self.buffersize = buffersize
        self.audio_sampling_rate = audio_sampling_rate
        self.target_audio_bitrate = target_audio_bitrate
        self.quality_range = quality_range
        self.ffmpeg_video_scale = ffmpeg_video_scale

    def update(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def to_ffmpeg_args(
        self,
        threads=8,
        max_muxing_queue_size=9999,
        extra_ffmpeg_params=[],
        custom_video_codec=None,
        custom_audio_codec=None,
        ffmpeg_cpu_used=0,
    ):
        arg_list = [
            "-codec:v",
            self.video_codecs[self.video_format]
            if custom_video_codec is None
            else custom_video_codec,
            "-codec:a",
            self.audio_codecs[self.video_format]
            if custom_audio_codec is None
            else custom_audio_codec,
            "-qmin",
            str(self.quality_range[0]),
            "-qmax",
            str(self.quality_range[1]),
            "-quality",
            "best",
            "-max_muxing_queue_size",
            str(max_muxing_queue_size),
            "-vf",
            f"scale='{self.ffmpeg_video_scale}'",
            "-ar",
            str(self.audio_sampling_rate),
            "-b:v",
            self.target_video_bitrate,
            "-b:a",
            self.target_audio_bitrate,
            "-maxrate",
            self.max_video_bitrate,
            "-bufsize",
            self.buffersize,
            "-threads",
            str(threads),
            "-cpu-used",
            str(ffmpeg_cpu_used),
        ]
        if self.min_video_bitrate is not None:
            arg_list += ["-minrate", str(self.min_video_bitrate)]

        if self.video_format in self.params:
            arg_list += self.params[self.video_format]

        if extra_ffmpeg_params:
            arg_list += extra_ffmpeg_params