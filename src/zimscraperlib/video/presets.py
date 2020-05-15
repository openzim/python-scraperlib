#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu


class VoiceMp3Low(dict):
    VERSION = 1

    options = {
        "-codec:a": "mp3",  # audio codec
        "-ar": "44100",  # audio sampling rate
        "-b:a": "48k",  # target audio bitrate
    }

    def __init__(self, **kwargs):
        super().__init__(self, **type(self).options)
        self.update(kwargs)

    def to_ffmpeg_args(self):
        """Convert the options dict to list of ffmpeg arguments"""

        args = []
        for k, v in self.items():
            args += [k, v]
        return args


class VideoWebmLow(dict):
    VERSION = 1

    options = {
        "-codec:v": "libvpx",  # video codec
        "-quality": "best",  # codec preset
        "-b:v": "300k",  # target video bitrate
        "-maxrate": "300k",  # max video bitrate
        "-bufsize": "1000k",  # buffer size
        "-minrate": "300k",  # min video bitrate
        "-codec:a": "libvorbis",  # audio codec
        "-qmin": "30",  # min quantizer scale
        "-qmax": "42",  # max quantizer scale
        "-vf": "scale='480:trunc(ow/a/2)*2'",  # frame size
        "-ar": "44100",  # audio sampling rate
        "-b:a": "48k",  # target audio bitrate
    }

    def __init__(self, **kwargs):
        super().__init__(self, **type(self).options)
        self.update(kwargs)

    def to_ffmpeg_args(self):
        """Convert the options dict to list of ffmpeg arguments"""

        args = []
        for k, v in self.items():
            args += [k, v]
        return args
