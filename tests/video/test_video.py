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


def download_media_and_reencode(
    temp_dir, src, dest, ffmpeg_args, download_links, **kwargs
):
    temp_dir_path = pathlib.Path(temp_dir)
    src_path = temp_dir_path.joinpath(src)
    dest_path = temp_dir_path.joinpath(dest)
    save_large_file(download_links[src_path.suffix.replace(".", "")], src_path)
    return reencode(src_path, dest_path, ffmpeg_args, **kwargs)


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
    config.update_from(**updates)
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
    )
    config.update_from()
    args = config.to_ffmpeg_args()
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
        assert idx != -1
        assert args[idx + 1] == str(getattr(config, attr))
    video_scale = getattr(config, "video_scale")
    qmin, qmax = getattr(config, "quantizer_scale_range")
    assert args.index("-qmin") != -1 and args[args.index("-qmin") + 1] == str(qmin)
    assert args.index("-qmax") != -1 and args[args.index("-qmax") + 1] == str(qmax)
    assert (
        args.index("-vf") != -1
        and args[args.index("-vf") + 1] == f"scale='{video_scale}'"
    )
    assert (
        args.index("-max_muxing_queue_size") != -1
        and args[args.index("-max_muxing_queue_size") + 1] == "9999"
    )

    with pytest.raises(ValueError):
        config.update_from(quantizer_scale_range=(-5, 52))


@pytest.mark.slow
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
        assert idx != -1
        assert args[idx + 1] == val

    # test updating values
    config = VideoWebmLow(**{"-ar": "50000"})
    config["-bufsize"] = "900k"
    args = config.to_ffmpeg_args()
    idx = args.index("-ar")
    assert idx != -1 and args[idx + 1] == "50000"
    idx = args.index("-bufsize")
    assert idx != -1 and args[idx + 1] == "900k"


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
        assert idx != -1
        assert args[idx + 1] == val

    # test updating values
    config = VoiceMp3Low(**{"-ar": "50000"})
    config["-b:a"] = "128k"
    args = config.to_ffmpeg_args()
    idx = args.index("-ar")
    assert idx != -1 and args[idx + 1] == "50000"
    idx = args.index("-b:a")
    assert idx != -1 and args[idx + 1] == "128k"


@pytest.mark.slow
@pytest.mark.parametrize(
    "src,dest,ffmpeg_args,expected",
    [
        (
            "video.mkv",
            "video.mp4",
            Config.build_from(
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
            ).to_ffmpeg_args(),
            {"codecs": ["h264", "aac"], "duration": 2},
        ),
        (
            "video.mp4",
            "video.webm",
            VideoWebmLow().to_ffmpeg_args(),
            {"codecs": ["vp8", "vorbis"], "duration": 2},
        ),
        (
            "video.webm",
            "video.mkv",
            [
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
            ],
            {"codecs": ["hevc", "vorbis"], "duration": 2},
        ),
        (
            "video.mp4",
            "audio.mp3",
            VoiceMp3Low().to_ffmpeg_args(),
            {"codecs": ["mp3"], "duration": 2},
        ),
    ],
)
def test_reencode_media(src, dest, ffmpeg_args, expected, hosted_media_links):
    with tempfile.TemporaryDirectory() as temp_dir:
        download_media_and_reencode(
            temp_dir, src, dest, ffmpeg_args, hosted_media_links
        )
        converted_details = get_media_info(pathlib.Path(temp_dir).joinpath(dest))
        assert expected["duration"] == converted_details["duration"]
        assert expected["codecs"] == converted_details["codecs"]


@pytest.mark.slow
@pytest.mark.parametrize(
    "src,dest,ffmpeg_args,delete_src",
    [
        ("video.mp4", "video.webm", VideoWebmLow().to_ffmpeg_args(), True,),
        ("video.mp4", "audio.mp3", VoiceMp3Low().to_ffmpeg_args(), False,),
    ],
)
def test_reencode_delete_src(src, dest, ffmpeg_args, delete_src, hosted_media_links):
    with tempfile.TemporaryDirectory() as temp_dir:
        download_media_and_reencode(
            temp_dir, src, dest, ffmpeg_args, hosted_media_links, delete_src=delete_src
        )
        src_path = pathlib.Path(temp_dir).joinpath(src)
        if delete_src:
            assert not src_path.exists()
        else:
            assert src_path.exists()


@pytest.mark.slow
@pytest.mark.parametrize(
    "src,dest,ffmpeg_args,return_output",
    [
        ("video.mp4", "video.webm", VideoWebmLow().to_ffmpeg_args(), True,),
        ("video.mp4", "audio.mp3", VoiceMp3Low().to_ffmpeg_args(), False,),
    ],
)
def test_reencode_return_ffmpeg_output(
    src, dest, ffmpeg_args, return_output, hosted_media_links
):
    with tempfile.TemporaryDirectory() as temp_dir:
        ret = download_media_and_reencode(
            temp_dir,
            src,
            dest,
            ffmpeg_args,
            hosted_media_links,
            with_process=return_output,
        )
        if return_output:
            success, stdout, stderr = ret
            assert success
            assert stdout is not None and stderr is not None
        else:
            assert ret


@pytest.mark.slow
@pytest.mark.parametrize(
    "src,dest,ffmpeg_args,failsafe",
    [
        ("video.webm", "video.mp4", ["-qmin", "-5"], True,),
        ("video.webm", "video.mp4", ["-qmin", "-5"], False,),
    ],
)
def test_reencode_failsafe(src, dest, ffmpeg_args, failsafe, hosted_media_links):
    with tempfile.TemporaryDirectory() as temp_dir:
        if not failsafe:
            with pytest.raises(subprocess.CalledProcessError):
                download_media_and_reencode(
                    temp_dir,
                    src,
                    dest,
                    ffmpeg_args,
                    hosted_media_links,
                    failsafe=failsafe,
                )
        else:
            success = download_media_and_reencode(
                temp_dir, src, dest, ffmpeg_args, hosted_media_links, failsafe=failsafe
            )
            assert not success
