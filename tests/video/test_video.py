#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import pytest
import tempfile
import pathlib

from zimscraperlib.download import save_large_file
from zimscraperlib.video import reencode, get_media_info
from zimscraperlib.video.presets import VoiceMp3Low, VideoWebmLow


def test_config_builder_defaults(config_builder):
    assert config_builder.video_codec == "h264"
    assert config_builder.audio_codec == "aac"
    assert config_builder.max_video_bitrate == "300k"
    assert config_builder.min_video_bitrate is None
    assert config_builder.target_video_bitrate == "300k"
    assert config_builder.buffersize == "1000k"
    assert config_builder.audio_sampling_rate == 44100
    assert config_builder.target_audio_bitrate == "128k"
    assert config_builder.quantizer_scale_range == (30, 42)
    assert config_builder.video_scale == "480:trunc(ow/a/2)*2"
    assert config_builder.extra_params == ["-movflags", "+faststart"]


def test_config_builder_update(config_builder):
    updates = {
        "min_video_bitrate": "300k",
        "quantizer_scale_range": (25, 35),
        "audio_sampling_rate": 51000,
    }
    config_builder.update(**updates)
    for k, v in updates.items():
        assert getattr(config_builder, k) == v


def test_config_builder_to_ffmpeg_args(config_builder):
    config_builder.update(min_video_bitrate="300k")
    args = config_builder.to_ffmpeg_args()
    assert len(args) == 24
    options_map = [
        ("codec:v", "video_codec"),
        ("codec:a", "audio_codec"),
        ("maxrate", "max_video_bitrate"),
        ("minrate", "min_video_bitrate"),
        ("b:v", "target_video_bitrate"),
        ("bufsize", "buffersize"),
        ("ar", "audio_sampling_rate"),
        ("b:a", "target_audio_bitrate"),
    ]
    for option, attr in options_map:
        idx = args.index(f"-{option}")
        assert idx >= 0
        assert args[idx + 1] == str(getattr(config_builder, attr))
    video_scale = getattr(config_builder, "video_scale")
    qmin, qmax = getattr(config_builder, "quantizer_scale_range")
    assert args[10:16] == [
        "-qmin",
        str(qmin),
        "-qmax",
        str(qmax),
        "-vf",
        f"scale='{video_scale}'",
    ]
    extra_params = [
        "-movflags",
        "+faststart",
    ]
    assert args[-2:] == extra_params

    # test wrong quantizer range
    config_builder.update(quantizer_scale_range=(-5, 2048))
    try:
        config_builder.to_ffmpeg_args()
    except ValueError as exc:
        assert str(exc) == "Quantizer scale must range from (-1, -1) to (69, 1024)"


@pytest.mark.slow
def test_get_media_info(hosted_media_links):
    with tempfile.TemporaryDirectory() as temp_dir:
        test_files = {
            "mkv": pathlib.Path(temp_dir).joinpath("video.mkv"),
            "mp4": pathlib.Path(temp_dir).joinpath("video.mp4"),
            "webm": pathlib.Path(temp_dir).joinpath("video.webm"),
            "mp3": pathlib.Path(temp_dir).joinpath("audio.mp3"),
        }
        for key, val in test_files.items():
            save_large_file(hosted_media_links[key], val)
        original_media_info = {
            "mkv": {"codecs": ["h264", "vorbis"], "duration": 2, "bitrate": 3819022},
            "mp4": {"codecs": ["h264", "aac"], "duration": 2, "bitrate": 3818365},
            "webm": {"codecs": ["vp9", "opus"], "duration": 2, "bitrate": 336650},
            "mp3": {"codecs": ["mp3"], "duration": 2, "bitrate": 129066},
        }
        for key, val in original_media_info.items():
            assert get_media_info(test_files[key]) == val


def test_preset_video_webm_low():
    config = VideoWebmLow()
    assert config.VERSION == 1
    args = config.to_ffmpeg_args()
    assert len(args) == 24
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
    assert len(args) == 6
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


@pytest.mark.slow
def test_reencode(config_builder, hosted_media_links):
    with tempfile.TemporaryDirectory() as temp_dir:
        src_video_path = pathlib.Path(temp_dir).joinpath("src_video.mp4")
        mp4_video_path = pathlib.Path(temp_dir).joinpath("video.mp4")
        webm_video_path = pathlib.Path(temp_dir).joinpath("video.webm")
        mkv_video_path = pathlib.Path(temp_dir).joinpath("video.mkv")
        mp3_audio_path = pathlib.Path(temp_dir).joinpath("audio.mp3")
        save_large_file(hosted_media_links["mp4"], src_video_path)
        original_details = get_media_info(src_video_path)
        # compress the video in mp4 format
        config = config_builder.to_ffmpeg_args()
        reencode(src_video_path, mp4_video_path, config, delete_src=False)
        mp4_converted_details = get_media_info(mp4_video_path)
        for codec in ["h264", "aac"]:
            assert codec in mp4_converted_details["codecs"]
        assert original_details["duration"] == mp4_converted_details["duration"]
        assert src_video_path.exists()

        # compress the video in webm format
        config = VideoWebmLow().to_ffmpeg_args()
        reencode(src_video_path, webm_video_path, config, delete_src=False)
        webm_converted_details = get_media_info(webm_video_path)
        for codec in ["vp8", "vorbis"]:
            assert codec in webm_converted_details["codecs"]
        assert original_details["duration"] == webm_converted_details["duration"]
        assert src_video_path.exists()

        # reencode to audio using preset
        config = VoiceMp3Low().to_ffmpeg_args()
        reencode(src_video_path, mp3_audio_path, config, delete_src=False)
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
        reencode(src_video_path, mkv_video_path, config, delete_src=True, threads=8)
        mkv_converted_details = get_media_info(mkv_video_path)
        for codec in ["hevc", "vorbis"]:
            assert codec in mkv_converted_details["codecs"]
        assert original_details["duration"] == mkv_converted_details["duration"]
        assert not src_video_path.exists()

        # check ffmpeg fail
        preset = VideoWebmLow()
        preset["-qmin"] = "-10"
        config = preset.to_ffmpeg_args()
        try:
            reencode(
                mp4_video_path, webm_video_path, config, delete_src=True, threads=8
            )
        except Exception as exc:
            assert str(exc) == "FFmpeg failed to run properly"
