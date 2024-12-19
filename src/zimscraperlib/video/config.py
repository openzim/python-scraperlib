from typing import Any, ClassVar


class Config(dict[str, str | None]):
    VERSION = 1
    ext = "dat"
    mimetype = "application/data"
    options: ClassVar[dict[str, str | None]] = {}
    defaults: ClassVar[dict[str, str | None]] = {"-max_muxing_queue_size": "9999"}
    mapping: ClassVar[dict[str, str]] = {
        "video_codec": "-codec:v",
        "audio_codec": "-codec:a",
        "max_video_bitrate": "-maxrate",
        "min_video_bitrate": "-minrate",
        "target_video_bitrate": "-b:v",
        "buffersize": "-bufsize",
        "audio_sampling_rate": "-ar",
        "target_audio_bitrate": "-b:a",
    }

    def __init__(self, **kwargs: Any):
        super().__init__(self, **type(self).defaults)
        self.update(self.options)
        self.update(kwargs)

    def update_from(self, **kwargs: Any):
        """Updates Config object based on shortcut params as given in build_from()"""

        for key, value in kwargs.items():
            setattr(self, key, value)

    def to_ffmpeg_args(self) -> list[str]:
        """Convert the options dict to list of ffmpeg arguments"""

        args: list[str] = []
        for k, v in self.items():
            if v:
                args += [k, v]
            else:
                args += [
                    k
                ]  # put only k in cases it's not followed by a value (boolean flag)
        return args

    @property
    def video_codec(self):
        return self.get(self.mapping["video_codec"])

    @video_codec.setter
    def video_codec(self, value: str):
        self[self.mapping["video_codec"]] = value

    @property
    def audio_codec(self):
        return self.get(self.mapping["audio_codec"])

    @audio_codec.setter
    def audio_codec(self, value: str):
        self[self.mapping["audio_codec"]] = value

    @property
    def max_video_bitrate(self):
        return self.get(self.mapping["max_video_bitrate"])

    @max_video_bitrate.setter
    def max_video_bitrate(self, value: str):
        self[self.mapping["max_video_bitrate"]] = value

    @property
    def min_video_bitrate(self):
        return self.get(self.mapping["min_video_bitrate"])

    @min_video_bitrate.setter
    def min_video_bitrate(self, value: str):
        self[self.mapping["min_video_bitrate"]] = value

    @property
    def target_video_bitrate(self):
        return self.get(self.mapping["target_video_bitrate"])

    @target_video_bitrate.setter
    def target_video_bitrate(self, value: str):
        self[self.mapping["target_video_bitrate"]] = value

    @property
    def target_audio_bitrate(self):
        return self.get(self.mapping["target_audio_bitrate"])

    @target_audio_bitrate.setter
    def target_audio_bitrate(self, value: str):
        self[self.mapping["target_audio_bitrate"]] = value

    @property
    def audio_sampling_rate(self):
        return self.get(self.mapping["audio_sampling_rate"])

    @audio_sampling_rate.setter
    def audio_sampling_rate(self, value: str):
        self[self.mapping["audio_sampling_rate"]] = value

    @property
    def buffersize(self):
        return self.get(self.mapping["buffersize"])

    @buffersize.setter
    def buffersize(self, value: str):
        self[self.mapping["buffersize"]] = value

    @property
    def video_scale(self) -> str | None:
        # remove "scale='" and "'" and return the value in between
        if vf := self.get("-vf", []):
            # test type to please type checker
            if not isinstance(vf, str):  # pragma: no cover
                raise Exception("Incorrect vf value")
            return vf[7:-1]
        return None

    @video_scale.setter
    def video_scale(self, value: str):
        self["-vf"] = f"scale='{value}'"

    @property
    def quantizer_scale_range(self):
        qmin = self.get("-qmin")
        qmax = self.get("-qmax")
        return (int(qmin), int(qmax)) if qmin is not None and qmax is not None else None

    @quantizer_scale_range.setter
    def quantizer_scale_range(self, value: tuple[int, int]):
        qmin, qmax = value
        if -1 <= qmin <= 69 and -1 <= qmax <= 1024:  # noqa: PLR2004
            self["-qmin"] = str(qmin)
            self["-qmax"] = str(qmax)
        else:
            raise ValueError(
                "Quantizer scale should be 2-int tuple ranging (-1, -1) to (69, 1024)"
            )

    @classmethod
    def build_from(cls, **params: Any):
        """build a Config easily via shortcut params

        video_codec: codec for output audio stream. more info
        https://ffmpeg.org/ffmpeg-codecs.html#Video-Encoders
            values: h264 | libvpx | libx264 | libx265 | xxx
        audio_codec: codec for output audio stream. more info
        https://ffmpeg.org/ffmpeg-codecs.html#Audio-Encoders
            values: aac | mp3 | flac | opus | libvorbis | xxx
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
        quantizer_scale_range: tuple of min / max values of video quantizer scale (VBR)
            values: (21, 35) | (68, 97) | (x, y)
        video_scale: video frame scale. more info - https://trac.ffmpeg.org/wiki/Scaling
            values: 480:320 | 320:240 | width:height
        """
        config = cls()
        config.update_from(**params)
        return config
