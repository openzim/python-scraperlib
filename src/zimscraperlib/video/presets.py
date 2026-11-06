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

    options: ClassVar[dict[str, str | None]] = {
        "-vn": "",  # remove video stream
        "-codec:a": "mp3",  # audio codec
        "-ar": "44100",  # audio sampling rate
        "-b:a": "48k",  # target audio bitrate
        "-ac": "2",  # force stereo
    }


class VideoWebmLow(Config):
    """Low Quality webm video

    480:h format with height adjusted to keep aspect ratio
    128k target video bitrate but stay within quality boundaries.
    48k audio bitrate"""

    VERSION = 4

    ext = "webm"
    mimetype = f"{preset_type}/webm"

    options: ClassVar[dict[str, str | None]] = {
        "-codec:v": "libvpx-vp9",  # video codec
        "-b:v": "140k",  # Adjust quantizer within min/max to target this bitrate
        "-qmin": "30",  # Reduce the bitrate on very still videos
        "-qmax": "40",  # Increase the bitrate on very busy videos
        "-g": "240",  # Number of frames allowed between keyframes
        "-quality": "good",  # codec preset
        "-speed": "4",  # Encoding speed (compromise between quality and encoding time)
        "-vf": "scale='480:trunc(ow/a/2)*2'",  # frame size
        "-row-mt": "1",
        "-codec:a": "libvorbis",  # audio codec
        "-b:a": "48k",  # target audio bitrate
        "-ar": "44100",  # audio sampling rate
        "-ac": "2",  # force stereo
    }


class VideoWebmMedium(Config):
    """Medium Quality webm video

    720:h format, height capped at 720 and width adjusted to keep aspect
    ratio, so smaller videos are not upscaled
    240k target video bitrate but stay within quality boundaries.
    48k audio bitrate"""

    VERSION = 1

    ext = "webm"
    mimetype = f"{preset_type}/webm"

    options: ClassVar[dict[str, str | None]] = {
        "-codec:v": "libvpx-vp9",
        "-b:v": "240k",
        "-qmin": "32",
        "-qmax": "58",
        "-g": "240",
        "-quality": "good",
        "-speed": "3",
        "-vf": "scale='-2:min(720,ih)':force_original_aspect_ratio=increase",
        "-row-mt": "1",
        "-codec:a": "libvorbis",
        "-b:a": "48k",
        "-ar": "44100",
        "-ac": "2",
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

    options: ClassVar[dict[str, str | None]] = {
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
        "-ac": "2",  # force stereo
    }


class VideoWebmHigh(Config):
    """High Quality webm video

    25 constant quality"""

    VERSION = 3

    ext = "webm"
    mimetype = f"{preset_type}/webm"

    options: ClassVar[dict[str, str | None]] = {
        "-codec:v": "libvpx-vp9",  # video codec
        "-b:v": "340k",  # Adjust quantizer within min/max to target this bitrate
        "-qmin": "26",  # Reduce the bitrate on very still videos
        "-qmax": "54",  # Increase the bitrate on very busy videos
        "-g": "240",  # Number of frames allowed between keyframes
        "-quality": "good",  # codec preset
        "-speed": "1",  # Encoding speed (compromise between quality and encoding time)
        "-row-mt": "1",
        "-codec:a": "libvorbis",  # audio codec
        "-b:a": "48k",  # target audio bitrate
        "-ar": "44100",  # audio sampling rate
        "-ac": "2",  # force stereo
    }


class VideoMp4High(Config):
    """High Quality mp4 video

    28 constant quality"""

    VERSION = 2

    ext = "mp4"
    mimetype = f"{preset_type}/mp4"

    options: ClassVar[dict[str, str | None]] = {
        "-codec:v": "h264",  # video codec
        "-codec:a": "aac",  # audio codec
        "-crf": "28",  # constant quality, lower value gives better qual and larger size
        "-movflags": "+faststart",
    }
