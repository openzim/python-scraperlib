#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import pathlib
import subprocess
import humanfriendly
import shutil

from zimscraperlib.download import save_large_file


def get_video_info(src_path):
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
    ffprobe = subprocess.run(args, capture_output=True, text=True, check=False)
    ffprobe_result = ffprobe.stdout.strip().split("\n")
    streams = ffprobe_result[:-1]
    codecs = [stream.split(",")[-1] for stream in streams]
    format = ffprobe_result[-1].split(",")[1:]
    vid_info = {
        "codecs": codecs,
        "duration": int(format[0].split(".")[0]),
        "bitrate": int(format[1]),
    }
    return vid_info


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
        assert ffargs[arg_index + 1] == str(getattr(vidcompressioncfg, attr))
    video_scale = getattr(vidcompressioncfg, "ffmpeg_video_scale")
    qmin, qmax = getattr(vidcompressioncfg, "quality_range")
    assert ffargs[14:20] == [
        "-qmin",
        str(qmin),
        "-qmax",
        str(qmax),
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


def test_video_recompression(
    vidutil, vidcompressioncfg, temp_video_dir, hosted_video_links
):
    temp_video_dir.mkdir(parents=True)
    src_video_path = temp_video_dir.joinpath("src_video.mp4")
    mp4_video_path = temp_video_dir.joinpath("video.mp4")
    webm_video_path = temp_video_dir.joinpath("video.webm")
    mkv_video_path = temp_video_dir.joinpath("video.mkv")
    save_large_file(hosted_video_links["mp4"], src_video_path)
    original_details = get_video_info(src_video_path)
    # compress the video in mp4 format
    vidutil.recompress_video(src_video_path, mp4_video_path, delete_src=False)
    mp4_converted_details = get_video_info(mp4_video_path)
    for codec in ["h264", "aac"]:
        assert codec in mp4_converted_details["codecs"]
    assert original_details["duration"] == mp4_converted_details["duration"]
    assert mp4_converted_details["bitrate"] <= humanfriendly.parse_size(
        getattr(vidcompressioncfg, "max_video_bitrate")
    )

    # compress the video in webm format
    vidutil.update(video_format="webm")
    vidutil.recompress_video(src_video_path, webm_video_path, delete_src=False)
    webm_converted_details = get_video_info(webm_video_path)
    for codec in ["vp8", "vorbis"]:
        assert codec in webm_converted_details["codecs"]
    assert original_details["duration"] == webm_converted_details["duration"]
    assert webm_converted_details["bitrate"] <= humanfriendly.parse_size(
        getattr(vidcompressioncfg, "max_video_bitrate")
    )
    assert src_video_path.exists()

    # try to compress in mkv without passing codecs and extra params list
    vidutil.update(video_format="mkv")
    try:
        vidutil.recompress_video(src_video_path, mkv_video_path)
    except TypeError as exc:
        assert (
            str(exc)
            == "The video format with which VidUtil is initialized requires audio_codec, video_codec and extra_ffmpeg_params to be passed as arguments"
        )

    # compress in mkv which is not supported by default
    vidutil.recompress_video(
        src_video_path,
        mkv_video_path,
        audio_codec="aac",
        video_codec="libx265",
        extra_ffmpeg_params=[],
    )
    mkv_converted_details = get_video_info(mkv_video_path)
    for codec in ["hevc", "aac"]:
        assert codec in mkv_converted_details["codecs"]
    assert original_details["duration"] == mkv_converted_details["duration"]
    assert not src_video_path.exists()
    shutil.rmtree(temp_video_dir)
