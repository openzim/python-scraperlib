#!/usr/bin/env python3
# vim: ai ts=4 sts=4 et sw=4 nu

import inspect
import pathlib
import shutil
import subprocess
import tempfile

import pytest

from zimscraperlib.video import Config, get_media_info, presets, reencode
from zimscraperlib.video.presets import (
    VideoMp4High,
    VideoMp4Low,
    VideoWebmHigh,
    VideoWebmLow,
    VoiceMp3Low,
)

ALL_PRESETS = [
    (n, p)
    for n, p in inspect.getmembers(presets)
    if inspect.isclass(p) and n != "Config"
]


def copy_media_and_reencode(temp_dir, src, dest, ffmpeg_args, test_files, **kwargs):
    src_path = temp_dir.joinpath(src)
    dest_path = temp_dir.joinpath(dest)
    shutil.copy2(test_files[src_path.suffix[1:]], src_path)
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
    video_scale = config.video_scale
    qmin, qmax = config.quantizer_scale_range  # pyright: ignore
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
        (
            "mp3",
            "audio.mp3",
            {"codecs": ["mp3"], "duration": 2, "bitrate": 129066},
        ),
    ],
)
def test_get_media_info(media_format, media, expected, test_files):
    with tempfile.TemporaryDirectory() as t:
        src = pathlib.Path(t).joinpath(media)
        shutil.copy2(test_files[media_format], src)
        result = get_media_info(src)
        assert result.keys() == expected.keys()
        assert result["codecs"] == expected["codecs"]
        assert result["duration"] == expected["duration"]
        # for bitrate, we need to allow some variability, not all ffmpeg version are
        # reporting the same values (e.g. Alpine Linux is reporting 3837275 instead of
        # 3818365 for video.mp4) ; we allow 1% variability with following assertion
        assert (
            abs(100.0 * (result["bitrate"] - expected["bitrate"]) / expected["bitrate"])
            < 1
        )


def test_preset_has_mime_and_ext():
    for _, preset in ALL_PRESETS:
        assert preset().ext
        assert preset().mimetype.split("/")[0] in ("audio", "video")


def test_preset_video_webm_low():
    config = VideoWebmLow()
    assert config.VERSION == 3
    args = config.to_ffmpeg_args()
    assert len(args) == 24
    options_map = [
        ("codec:v", "libvpx-vp9"),
        ("codec:a", "libvorbis"),
        ("b:v", "140k"),
        ("ar", "44100"),
        ("b:a", "48k"),
        ("quality", "good"),
        ("qmin", "30"),
        ("qmax", "40"),
        ("vf", "scale='480:trunc(ow/a/2)*2'"),
        ("g", "240"),
        ("speed", "4"),
    ]
    for option, val in options_map:
        idx = args.index(f"-{option}")
        assert idx != -1
        assert args[idx + 1] == val

    # test updating values
    config = VideoWebmLow(**{"-ar": "50000"})
    config["-qmin"] = "25"
    args = config.to_ffmpeg_args()
    idx = args.index("-ar")
    assert idx != -1 and args[idx + 1] == "50000"
    idx = args.index("-qmin")
    assert idx != -1 and args[idx + 1] == "25"


def test_preset_video_webm_high():
    config = VideoWebmHigh()
    assert config.VERSION == 2
    args = config.to_ffmpeg_args()
    assert len(args) == 22
    options_map = [
        ("codec:v", "libvpx-vp9"),
        ("codec:a", "libvorbis"),
        ("b:v", "340k"),
        ("ar", "44100"),
        ("b:a", "48k"),
        ("quality", "good"),
        ("qmin", "26"),
        ("qmax", "54"),
        ("g", "240"),
        ("speed", "1"),
    ]
    for option, val in options_map:
        idx = args.index(f"-{option}")
        assert idx != -1
        assert args[idx + 1] == val

    # test updating values
    config = VideoWebmHigh(**{"-qmax": "51"})
    config["-b:v"] = "300k"
    args = config.to_ffmpeg_args()
    idx = args.index("-qmax")
    assert idx != -1 and args[idx + 1] == "51"
    idx = args.index("-b:v")
    assert idx != -1 and args[idx + 1] == "300k"


def test_preset_video_mp4_low():
    config = VideoMp4Low()
    assert config.VERSION == 1
    args = config.to_ffmpeg_args()
    assert len(args) == 24
    options_map = [
        ("codec:v", "h264"),
        ("codec:a", "aac"),
        ("maxrate", "300k"),
        ("minrate", "300k"),
        ("b:v", "300k"),
        ("ar", "44100"),
        ("b:a", "48k"),
        ("movflags", "+faststart"),
        ("qmin", "30"),
        ("qmax", "42"),
        ("vf", "scale='480:trunc(ow/a/2)*2'"),
    ]
    for option, val in options_map:
        idx = args.index(f"-{option}")
        assert idx != -1
        assert args[idx + 1] == val

    # test updating values
    config = VideoMp4Low(**{"-ar": "50000"})
    config["-bufsize"] = "900k"
    args = config.to_ffmpeg_args()
    idx = args.index("-ar")
    assert idx != -1 and args[idx + 1] == "50000"
    idx = args.index("-bufsize")
    assert idx != -1 and args[idx + 1] == "900k"


def test_preset_video_mp4_high():
    config = VideoMp4High()
    assert config.VERSION == 1
    args = config.to_ffmpeg_args()
    assert len(args) == 8
    options_map = [
        ("codec:v", "h264"),
        ("codec:a", "aac"),
        ("crf", "20"),
    ]
    for option, val in options_map:
        idx = args.index(f"-{option}")
        assert idx != -1
        assert args[idx + 1] == val

    # test updating values
    config = VideoMp4Low(**{"-codec:v": "libx264"})
    config["-crf"] = "11"
    args = config.to_ffmpeg_args()
    idx = args.index("-codec:v")
    assert idx != -1 and args[idx + 1] == "libx264"
    idx = args.index("-crf")
    assert idx != -1 and args[idx + 1] == "11"


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
            {"codecs": ["vp9", "vorbis"], "duration": 2},
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
def test_reencode_media(src, dest, ffmpeg_args, expected, test_files):
    with tempfile.TemporaryDirectory() as t:
        temp_dir = pathlib.Path(t)
        copy_media_and_reencode(temp_dir, src, dest, ffmpeg_args, test_files)
        converted_details = get_media_info(temp_dir.joinpath(dest))
        assert expected["duration"] == converted_details["duration"]
        assert expected["codecs"] == converted_details["codecs"]


@pytest.mark.slow
@pytest.mark.parametrize(
    "src,dest,ffmpeg_args,delete_src",
    [
        (
            "video.mp4",
            "video.webm",
            VideoWebmLow().to_ffmpeg_args(),
            True,
        ),
        (
            "video.mp4",
            "audio.mp3",
            VoiceMp3Low().to_ffmpeg_args(),
            False,
        ),
    ],
)
def test_reencode_delete_src(src, dest, ffmpeg_args, delete_src, test_files):
    with tempfile.TemporaryDirectory() as t:
        temp_dir = pathlib.Path(t)
        src_path = temp_dir.joinpath(src)

        copy_media_and_reencode(
            temp_dir, src, dest, ffmpeg_args, test_files, delete_src=delete_src
        )
        if delete_src:
            assert not src_path.exists()
        else:
            assert src_path.exists()


@pytest.mark.slow
@pytest.mark.parametrize(
    "src,dest,ffmpeg_args,return_output",
    [
        (
            "video.mp4",
            "video.webm",
            VideoWebmLow().to_ffmpeg_args(),
            True,
        ),
        (
            "video.mp4",
            "audio.mp3",
            VoiceMp3Low().to_ffmpeg_args(),
            False,
        ),
    ],
)
def test_reencode_return_ffmpeg_output(
    src, dest, ffmpeg_args, return_output, test_files
):
    with tempfile.TemporaryDirectory() as t:
        temp_dir = pathlib.Path(t)
        ret = copy_media_and_reencode(
            temp_dir,
            src,
            dest,
            ffmpeg_args,
            test_files,
            with_process=return_output,
        )
        if return_output:
            success, process = ret  # pyright: ignore
            assert success
            assert len(process.stdout) > 0
        else:
            assert ret


@pytest.mark.slow
@pytest.mark.parametrize(
    "src,dest,ffmpeg_args,failsafe",
    [
        (
            "video.webm",
            "video.mp4",
            ["-qmin", "-5"],
            True,
        ),
        (
            "video.webm",
            "video.mp4",
            ["-qmin", "-5"],
            False,
        ),
    ],
)
def test_reencode_failsafe(src, dest, ffmpeg_args, failsafe, test_files):
    with tempfile.TemporaryDirectory() as t:
        temp_dir = pathlib.Path(t)
        if not failsafe:
            with pytest.raises(subprocess.CalledProcessError) as exc_info:
                copy_media_and_reencode(
                    temp_dir,
                    src,
                    dest,
                    ffmpeg_args,
                    test_files,
                    failsafe=failsafe,
                )
            assert len(exc_info.value.stdout) > 0

        else:
            success = copy_media_and_reencode(
                temp_dir, src, dest, ffmpeg_args, test_files, failsafe=failsafe
            )
            assert not success
