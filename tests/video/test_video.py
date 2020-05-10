#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import pathlib
import subprocess


def test_vidcompressioncfg_defaults(vidcompressioncfg):
    assert vidcompressioncfg.max_video_bitrate == "300k"
    assert vidcompressioncfg.min_video_bitrate is None
    assert vidcompressioncfg.target_video_bitrate == "300k"
    assert vidcompressioncfg.buffersize == "1000k"
    assert vidcompressioncfg.audio_sampling_rate == 44100
    assert vidcompressioncfg.target_audio_bitrate == "128k"
    assert vidcompressioncfg.ffmpeg_video_scale == "480:trunc(ow/a/2)*2"
    qmin, qmax = vidcompressioncfg.quality_range
    assert qmin == 30
    assert qmax == 42


def test_vidcompressioncfg_update(vidcompressioncfg):
    updates = {
        "min_video_bitrate": "300k",
        "quality_range": (25, 35),
        "audio_sampling_rate": 50000,
    }
    vidcompressioncfg.update(**updates)
    for k, v in updates.items():
        assert getattr(vidcompressioncfg, k) == v


def test_ffmpeg_args(vidcompressioncfg):
    vidcompressioncfg.update(min_video_bitrate="300k")
    ffargs = vidcompressioncfg.to_ffmpeg_args(
        video_codec="h264",
        audio_codec="aac",
        extra_ffmpeg_params=["-movflags", "+faststart"],
    )
    assert len(ffargs) == 32
    options_map = [
        ("maxrate", "max_video_bitrate"),
        ("b:v", "target_video_bitrate"),
        ("bufsize", "buffersize"),
        ("ar", "audio_sampling_rate"),
        ("b:a", "target_audio_bitrate"),
        ("quality", "quality"),
        ("minrate", "min_video_bitrate"),
    ]
    for index, option_data in enumerate(options_map):
        option, attr = option_data
        arg_index = index * 2
        assert ffargs[arg_index] == f"-{option}"
        assert ffargs[arg_index + 1] == getattr(vidcompressioncfg, attr)
    video_scale = getattr(vidcompressioncfg, "ffmpeg_video_scale")
    qmin, qmax = getattr(vidcompressioncfg, "quality_range")
    assert ffargs[14:20] == [
        "-qmin",
        qmin,
        "-qmax",
        qmax,
        "-vf",
        f"scale='{video_scale}'",
    ]
    param_matching_list = [
        "-codec:v",
        "h264",
        "-codec:a",
        "aac",
        "-max_muxing_queue_size",
        "9999",
        "-threads",
        "8",
        "-cpu-used",
        "0",
        "-movflags",
        "+faststart",
    ]
    assert ffargs[20:] == param_matching_list


def test_vidutil_update(vidutil, vidcompressioncfg):
    vidcompressioncfg.update(min_video_bitrate="100k")
    updates = {
        "video_format": "webm",
        "video_compression_cfg": vidcompressioncfg,
        "recompress": False,
    }
    vidutil.update(**updates)
    for k, v in updates.items():
        assert getattr(vidutil, k) == v
