#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import pytest
import tempfile
import pathlib
import subprocess

from zimscraperlib.download import save_large_file
from zimscraperlib.video.config import Config
from zimscraperlib.video.presets import VoiceMp3Low, VideoWebmLow
from zimscraperlib.video.encoding import reencode
from zimscraperlib.video.probing import get_media_info


def test_config_defaults():
    config = Config()
    assert config.VERSION == 1
    assert config.defaults == {"-max_muxing_queue_size": "9999"}
    args = config.to_ffmpeg_args()
    assert args == ["-max_muxing_queue_size", "9999"]


def test_config_update():
    config = Config()
    updates = {
        "min_video_bitrate": "300k",
        "quantizer_scale_range": (25, 35),
        "audio_sampling_rate": "51000",
        "video_scale": "480:trunc(ow/a/2)*2",
    }
    config.update_config(**updates)
    for k, v in updates.items():
        assert getattr(config, k) == v


def test_config_build_from():
    config = Config.build_from(
        video_codec="h264",
        audio_codec="aac",
        max_video_bitrate="500k",
        min_video_bitrate="500k",
        target_video_bitrate="500k",
        target_audio_bitrate="128k",
        buffersize="900k",
        audio_sampling_rate="44100",
        quantizer_scale_range=(21, 35),
        video_scale="480:trunc(ow/a/2)*2",
        threads=8,
    )
    config.update_config(extras=["-movflags", "+faststart"])
    args = config.to_ffmpeg_args()
    assert len(args) == 28
    options_map = [
        ("codec:v", "video_codec"),
        ("codec:a", "audio_codec"),
        ("maxrate", "max_video_bitrate"),
        ("minrate", "min_video_bitrate"),
        ("b:v", "target_video_bitrate"),
        ("bufsize", "buffersize"),
        ("ar", "audio_sampling_rate"),
        ("b:a", "target_audio_bitrate"),
        ("threads", "threads"),
    ]
    for option, attr in options_map:
        idx = args.index(f"-{option}")
        assert idx >= 0
        assert args[idx + 1] == str(getattr(config, attr))
    video_scale = getattr(config, "video_scale")
    qmin, qmax = getattr(config, "quantizer_scale_range")
    assert args.index("-qmin") >= 0 and args[args.index("-qmin") + 1] == str(qmin)
    assert args.index("-qmax") >= 0 and args[args.index("-qmax") + 1] == str(qmax)
    assert (
        args.index("-vf") >= 0
        and args[args.index("-vf") + 1] == f"scale='{video_scale}'"
    )
    assert (
        args.index("-max_muxing_queue_size") >= 0
        and args[args.index("-max_muxing_queue_size") + 1] == "9999"
    )
    extra_params = [
        "-movflags",
        "+faststart",
    ]
    assert args[-2:] == extra_params

    with pytest.raises(ValueError):
        config.update_config(quantizer_scale_range=(-5, 52))


@pytest.mark.parametrize(
    "media_format,media,expected",
    [
        (
            "mkv",
            "video.mkv",
            {"codecs": ["h264", "vorbis"], "duration": 2, "bitrate": 3819022},
        ),
        (
            "mp4",
            "video.mp4",
            {"codecs": ["h264", "aac"], "duration": 2, "bitrate": 3818365},
        ),
        (
            "webm",
            "video.webm",
            {"codecs": ["vp9", "opus"], "duration": 2, "bitrate": 336650},
        ),
        ("mp3", "audio.mp3", {"codecs": ["mp3"], "duration": 2, "bitrate": 129066},),
    ],
)
def test_get_media_info(media_format, media, expected, hosted_media_links):
    with tempfile.TemporaryDirectory() as temp_dir:
        src = pathlib.Path(temp_dir).joinpath(media)
        save_large_file(hosted_media_links[media_format], src)
        assert get_media_info(src) == expected


def test_preset_video_webm_low():
    config = VideoWebmLow()
    assert config.VERSION == 1
    args = config.to_ffmpeg_args()
    assert len(args) == 26
    options_map = [
        ("codec:v", "libvpx"),
        ("codec:a", "libvorbis"),
        ("maxrate", "300k"),
        ("minrate", "300k"),
        ("b:v", "300k"),
        ("bufsize", "1000k"),
        ("ar", "44100"),
        ("b:a", "48k"),
        ("quality", "best"),
        ("qmin", "30"),
        ("qmax", "42"),
        ("vf", "scale='480:trunc(ow/a/2)*2'"),
    ]
    for option, val in options_map:
        idx = args.index(f"-{option}")
        assert idx >= 0
        assert args[idx + 1] == val

    # test updating values
    config = VideoWebmLow(**{"-ar": "50000"})
    config["-bufsize"] = "900k"
    args = config.to_ffmpeg_args()
    idx = args.index("-ar")
    assert idx >= 0 and args[idx + 1] == "50000"
    idx = args.index("-bufsize")
    assert idx >= 0 and args[idx + 1] == "900k"


def test_preset_voice_mp3_low():
    config = VoiceMp3Low()
    assert config.VERSION == 1
    args = config.to_ffmpeg_args()
    assert len(args) == 9
    options_map = [
        ("codec:a", "mp3"),
        ("ar", "44100"),
        ("b:a", "48k"),
    ]
    for option, val in options_map:
        idx = args.index(f"-{option}")
        assert idx >= 0
        assert args[idx + 1] == val

    # test updating values
    config = VoiceMp3Low(**{"-ar": "50000"})
    config["-b:a"] = "128k"
    args = config.to_ffmpeg_args()
    idx = args.index("-ar")
    assert idx >= 0 and args[idx + 1] == "50000"
    idx = args.index("-b:a")
    assert idx >= 0 and args[idx + 1] == "128k"


# @pytest.mark.slow
def test_reencode_video(hosted_media_links):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = pathlib.Path(temp_dir)
        src_video_path = temp_dir.joinpath("src_video.mp4")
        mp4_video_path = temp_dir.joinpath("video.mp4")
        webm_video_path = temp_dir.joinpath("video.webm")
        mkv_video_path = temp_dir.joinpath("video.mkv")
        mp3_audio_path = temp_dir.joinpath("audio.mp3")
        save_large_file(hosted_media_links["mp4"], src_video_path)
        original_details = get_media_info(src_video_path)
        # compress the video in mp4 format
        config = Config.build_from(
            video_codec="h264",
            audio_codec="aac",
            max_video_bitrate="500k",
            min_video_bitrate="500k",
            target_video_bitrate="500k",
            target_audio_bitrate="128k",
            buffersize="900k",
            audio_sampling_rate="44100",
            quantizer_scale_range=(21, 35),
            video_scale="480:trunc(ow/a/2)*2",
            threads=8,
        ).to_ffmpeg_args()
        reencode(src_video_path, mp4_video_path, config)
        mp4_converted_details = get_media_info(mp4_video_path)
        for codec in ["h264", "aac"]:
            assert codec in mp4_converted_details["codecs"]
        assert original_details["duration"] == mp4_converted_details["duration"]
        assert src_video_path.exists()

        # compress the video in webm format
        config = VideoWebmLow().to_ffmpeg_args()
        reencode(src_video_path, webm_video_path, config)
        webm_converted_details = get_media_info(webm_video_path)
        for codec in ["vp8", "vorbis"]:
            assert codec in webm_converted_details["codecs"]
        assert original_details["duration"] == webm_converted_details["duration"]
        assert src_video_path.exists()

        # reencode to audio using preset
        config = VoiceMp3Low().to_ffmpeg_args()
        ret = reencode(src_video_path, mp3_audio_path, config)
        assert ret == 0
        mp3_converted_details = get_media_info(mp3_audio_path)
        assert original_details["duration"] == mp3_converted_details["duration"]
        assert src_video_path.exists()

        # compress in mkv with custom config as a param list
        config = [
            # video codec
            "-codec:v",
            "libx265",
            # target video bitrate
            "-b:v",
            "300k",
            # change output video dimensions
            "-vf",
            "scale='480:trunc(ow/a/2)*2'",
            # audio codec
            "-codec:a",
            "libvorbis",
            # audio sampling rate
            "-ar",
            "44100",
            # target audio bitrate
            "-b:a",
            "128k",
        ]
        out, ret = reencode(
            src_video_path, mkv_video_path, config, delete_src=True, return_output=True
        )
        assert len(out) > 0 and ret == 0
        mkv_converted_details = get_media_info(mkv_video_path)
        for codec in ["hevc", "vorbis"]:
            assert codec in mkv_converted_details["codecs"]
        assert original_details["duration"] == mkv_converted_details["duration"]
        assert not src_video_path.exists()

        # check ffmpeg fail and return ffmpeg output
        preset = VideoWebmLow()
        preset["-qmin"] = "-10"
        config = preset.to_ffmpeg_args()
        out, ret = reencode(
            mp4_video_path, webm_video_path, config, delete_src=True, return_output=True
        )
        assert len(out) > 0 and ret != 0
