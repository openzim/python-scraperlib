#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu


class Config(dict):
    VERSION = 1
    options = {}
    extras = []
    defaults = {"-max_muxing_queue_size": "9999"}
    mapping = {
        "video_codec": "-codec:v",
        "audio_codec": "-codec:a",
        "max_video_bitrate": "-maxrate",
        "min_video_bitrate": "-minrate",
        "target_video_bitrate": "-b:v",
        "buffersize": "-bufsize",
        "audio_sampling_rate": "-ar",
        "target_audio_bitrate": "-b:a",
        "threads": "-threads",
    }

    def __init__(self, **kwargs):
        super().__init__(self, **type(self).defaults)
        self.update(self.options)
        self.update(kwargs)

    def update_config(self, **kwargs):
        """Updates config based on shortcut params as given in build_from()"""

        for key, value in kwargs.items():
            setattr(self, key, value)

    def to_ffmpeg_args(self):
        """Convert the options dict to list of ffmpeg arguments"""

        args = []
        for k, v in self.items():
            args += [k, v]
        args += self.extras
        return args

    @property
    def video_codec(self):
        return self.get(self.mapping["video_codec"])

    @video_codec.setter
    def video_codec(self, value):
        self[self.mapping["video_codec"]] = value

    @property
    def audio_codec(self):
        return self.get(self.mapping["audio_codec"])

    @audio_codec.setter
    def audio_codec(self, value):
        self[self.mapping["audio_codec"]] = value

    @property
    def max_video_bitrate(self):
        return self.get(self.mapping["max_video_bitrate"])

    @max_video_bitrate.setter
    def max_video_bitrate(self, value):
        self[self.mapping["max_video_bitrate"]] = value

    @property
    def min_video_bitrate(self):
        return self.get(self.mapping["min_video_bitrate"])

    @min_video_bitrate.setter
    def min_video_bitrate(self, value):
        self[self.mapping["min_video_bitrate"]] = value

    @property
    def target_video_bitrate(self):
        return self.get(self.mapping["target_video_bitrate"])

    @target_video_bitrate.setter
    def target_video_bitrate(self, value):
        self[self.mapping["target_video_bitrate"]] = value

    @property
    def target_audio_bitrate(self):
        return self.get(self.mapping["target_audio_bitrate"])

    @target_audio_bitrate.setter
    def target_audio_bitrate(self, value):
        self[self.mapping["target_audio_bitrate"]] = value

    @property
    def audio_sampling_rate(self):
        return self.get(self.mapping["audio_sampling_rate"])

    @audio_sampling_rate.setter
    def audio_sampling_rate(self, value):
        self[self.mapping["audio_sampling_rate"]] = value

    @property
    def buffersize(self):
        return self.get(self.mapping["buffersize"])

    @buffersize.setter
    def buffersize(self, value):
        self[self.mapping["buffersize"]] = value

    @property
    def video_scale(self):
        scale = self.get("-vf")
        return scale[7:-1]

    @video_scale.setter
    def video_scale(self, value):
        self["-vf"] = f"scale='{value}'"

    @property
    def quantizer_scale_range(self):
        qmin = self.get("-qmin")
        qmax = self.get("-qmax")
        return (int(qmin), int(qmax))

    @quantizer_scale_range.setter
    def quantizer_scale_range(self, value):
        qmin, qmax = value
        if -1 <= qmin <= 69 and -1 <= qmax <= 1024:
            self["-qmin"] = str(qmin)
            self["-qmax"] = str(qmax)
        else:
            raise ValueError("Quantizer scale must range from (-1, -1) to (69, 1024)")

    @property
    def threads(self):
        return int(self.get(self.mapping["threads"]))

    @threads.setter
    def threads(self, value):
        self[self.mapping["threads"]] = str(value)

    @classmethod
    def build_from(cls, **params):
        """ build a Config easily via shortcut params

            video_codec: codec for output audio stream
                values: h264 | xxx
            audio_codec: codec for output audio stream
                values: aac | mp3 | xxx
            max_video_bitrate: maximum size per second for video stream
                values: 128k | 1m
            min_video_bitrate: minimum size per second for video stream
                values: 128k | 1m
            target_video_bitrate: tentative size per second for video stream
                values: 384k | 1m
            target_audio_bitrate: tentative size per second for audio stream
                values: 48k | 128k
            buffersize: decoder buffer size
                values: 1000k | 1m
            audio_sampling_rate: number of audio samples per second
                values: 44100 | 48000
            quantizer_scale_range: tuple of min and max values of video quantizer scale (VBR)
                values: (21, 35) | (68, 97) | (x, y)
            video_scale: video frame scale
                values: 480:trunc(ow/a/2)*2
            threads: number of threads to use
                values: 2 | 4 | 8 | x
            extras: list of extra ffmpeg arguments. always appended at the end
                values: ["-movflags", "+faststart"]
        """
        config = cls()
        for k, v in params.items():
            setattr(config, k, v)
        return config
