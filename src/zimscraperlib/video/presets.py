#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu


class VoiceMp3Low(dict):
    VERSION = 1

    options = {
        "-codec:a": "mp3",
        "-ar": "44100",  # set sample rate
        "-b:a": "48k",  # constant bitrate
    }

    def __init__(self, **kwargs):
        super().__init__(self, **type(self).options)
        self.update(kwargs)

    def to_ffmpeg_args(self):
        args = []
        for k, v in self.items():
            args += [k, v]
        return args


class VideoWebmLow(dict):
    VERSION = 1

    options = {
        "-codec:v": "libvpx",  # video codec
        "-quality": "best",
        "-b:v": "300k",
        "-maxrate": "300k",
        "-bufsize": "1000k",
        "-minrate": "300k",
        "-codec:a": "libvorbis",
        "-qmin": "30",
        "-qmax": "42",
        "-vf": "scale='480:trunc(ow/a/2)*2'",
        "-ar": "44100",
        "-b:a": "48k",
    }

    def __init__(self, **kwargs):
        super().__init__(self, **type(self).options)
        self.update(kwargs)

    def to_ffmpeg_args(self):
        args = []
        for k, v in self.items():
            args += [k, v]
        return args
