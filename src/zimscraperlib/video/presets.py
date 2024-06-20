#!/usr/bin/env python3
# vim: ai ts=4 sts=4 et sw=4 nu

from __future__ import annotations

from typing import ClassVar

from zimscraperlib.video.config import Config

preset_type = "video"


class VoiceMp3Low(Config):
    """Low quality mp3 audio

    44Khz audio sampling
    48k audio bitrate
    audio-only"""

    VERSION = 1

    ext = "mp3"
    mimetype = "audio/mp3"

    options: ClassVar[dict[str, str | bool | int | None]] = {
        "-vn": "",  # remove video stream
        "-codec:a": "mp3",  # audio codec
        "-ar": "44100",  # audio sampling rate
        "-b:a": "48k",  # target audio bitrate
    }


class VideoWebmLow(Config):
    """Low Quality webm video

    480:h format with height adjusted to keep aspect ratio
    128k target video bitrate but stay within quality boundaries.
    48k audio bitrate"""

    VERSION = 3

    ext = "webm"
    mimetype = f"{preset_type}/webm"

    options: ClassVar[dict[str, str | bool | int | None]] = {
        "-codec:v": "libvpx-vp9",  # video codec
        "-b:v": "140k",  # Adjust quantizer within min/max to target this bitrate
        "-qmin": "30",  # Reduce the bitrate on very still videos
        "-qmax": "40",  # Increase the bitrate on very busy videos
        "-g": "240",  # Number of frames allowed between keyframes
        "-quality": "good",  # codec preset
        "-speed": "4",  # Encoding speed (compromise between quality and encoding time)
        "-vf": "scale='480:trunc(ow/a/2)*2'",  # frame size
        "-codec:a": "libvorbis",  # audio codec
        "-b:a": "48k",  # target audio bitrate
        "-ar": "44100",  # audio sampling rate
    }


class VideoMp4Low(Config):
    """Low Quality mp4 video

    480:h format with height adjusted to keep aspect ratio
    300k video bitrate
    48k audio bitrate
    highly degraded quality (30, 42)"""

    VERSION = 1

    ext = "mp4"
    mimetype = f"{preset_type}/mp4"

    options: ClassVar[dict[str, str | bool | int | None]] = {
        "-codec:v": "h264",  # video codec
        "-b:v": "300k",  # target video bitrate
        "-maxrate": "300k",  # max video bitrate
        "-minrate": "300k",  # min video bitrate
        "-qmin": "30",  # min quantizer scale
        "-qmax": "42",  # max quantizer scale
        "-vf": "scale='480:trunc(ow/a/2)*2'",  # frame size
        "-codec:a": "aac",  # audio codec
        "-ar": "44100",  # audio sampling rate
        "-b:a": "48k",  # target audio bitrate
        "-movflags": "+faststart",  # extra flag
    }


class VideoWebmHigh(Config):
    """High Quality webm video

    25 constant quality"""

    VERSION = 2

    ext = "webm"
    mimetype = f"{preset_type}/webm"

    options: ClassVar[dict[str, str | bool | int | None]] = {
        "-codec:v": "libvpx-vp9",  # video codec
        "-b:v": "340k",  # Adjust quantizer within min/max to target this bitrate
        "-qmin": "26",  # Reduce the bitrate on very still videos
        "-qmax": "54",  # Increase the bitrate on very busy videos
        "-g": "240",  # Number of frames allowed between keyframes
        "-quality": "good",  # codec preset
        "-speed": "1",  # Encoding speed (compromise between quality and encoding time)
        "-codec:a": "libvorbis",  # audio codec
        "-b:a": "48k",  # target audio bitrate
        "-ar": "44100",  # audio sampling rate
    }


class VideoMp4High(Config):
    """Low Quality mp4 video

    20 constant quality"""

    VERSION = 1

    ext = "mp4"
    mimetype = f"{preset_type}/mp4"

    options: ClassVar[dict[str, str | bool | int | None]] = {
        "-codec:v": "h264",  # video codec
        "-codec:a": "aac",  # audio codec
        "-crf": "20",  # constant quality, lower value gives better qual and larger size
    }
