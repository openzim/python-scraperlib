#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import subprocess

from . import logger
from .logging import nicer_args_join


class VidCompressionCfg(object):
    def __init__(
        self,
        max_video_bitrate="300k",
        min_video_bitrate=None,
        target_video_bitrate="300k",
        buffersize="1000k",
        audio_sampling_rate=44100,
        target_audio_bitrate="128k",
        quality_range=(30, 42),
        ffmpeg_video_scale="480:trunc(ow/a/2)*2",
    ):
        self.max_video_bitrate = max_video_bitrate
        self.min_video_bitrate = min_video_bitrate
        self.target_video_bitrate = target_video_bitrate
        self.buffersize = buffersize
        self.audio_sampling_rate = audio_sampling_rate
        self.target_audio_bitrate = target_audio_bitrate
        self.quality_range = quality_range
        self.ffmpeg_video_scale = ffmpeg_video_scale

    def update(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def to_ffmpeg_args(
        self,
        threads=8,
        max_muxing_queue_size=9999,
        extra_ffmpeg_params=[],
        video_codec=None,
        audio_codec=None,
        ffmpeg_cpu_used=0,
    ):
        arg_list = [
            "-codec:v",
            video_codec,
            "-codec:a",
            audio_codec,
            "-qmin",
            str(self.quality_range[0]),
            "-qmax",
            str(self.quality_range[1]),
            "-quality",
            "best",
            "-max_muxing_queue_size",
            str(max_muxing_queue_size),
            "-vf",
            f"scale='{self.ffmpeg_video_scale}'",
            "-ar",
            str(self.audio_sampling_rate),
            "-b:v",
            self.target_video_bitrate,
            "-b:a",
            self.target_audio_bitrate,
            "-maxrate",
            self.max_video_bitrate,
            "-bufsize",
            self.buffersize,
            "-threads",
            str(threads),
            "-cpu-used",
            str(ffmpeg_cpu_used),
        ]
        if self.min_video_bitrate:
            arg_list += ["-minrate", str(self.min_video_bitrate)]

        arg_list += extra_ffmpeg_params


class VidUtil(object):
    default_video_formats = {
        "mp4": {
            "vcodec": "h264",
            "acodec": "aac",
            "params": ["-movflags", "+faststart"],
        },
        "webm": {"vcodec": "libvpx", "acodec": "libvorbis", "params": [],},
    }

    def __init__(
        self, video_compression_cfg, video_format, recompress,
    ):
        self.video_format = video_format
        self.video_compression_cfg = video_compression_cfg
        self.recompress = recompress

    def recompress_video(self, src_path, dst_path, **kwargs):
        if self.video_format in self.default_video_formats:
            audio_codec = self.default_video_formats[self.video_format]["acodec"]
            video_codec = self.default_video_formats[self.video_format]["vcodec"]
            extra_ffmpeg_params = self.default_video_formats[self.video_format][
                "params"
            ]
        elif (
            "audio_codec" in kwargs
            and "video_codec" in kwargs
            and "extra_ffmpeg_params" in kwargs
        ):
            audio_codec = kwargs["audio_codec"]
            video_codec = kwargs["video_codec"]
            extra_ffmpeg_params = kwargs["extra_ffmpeg_params"]
            for key in ["audio_codec", "video_codec", "extra_ffmpeg_params"]:
                del kwargs[key]
        else:
            raise TypeError(
                "The video format with which VidUtil is initialized requires audio_codec, video_codec and extra_ffmpeg_params to be passed as arguments"
            )

        tmp_path = src_path.parent.joinpath(f"video.tmp.{self.video_format}")
        args = (
            ["ffmpeg", "-y", "-i", f"file:{src_path}"]
            + self.video_compression_cfg.to_ffmpeg_args(
                audio_codec=audio_codec,
                video_codec=video_codec,
                extra_ffmpeg_params=extra_ffmpeg_params,
                **kwargs,
            )
            + [f"file:{tmp_path}"]
        )
        logger.info(f"recompress {src_path} -> {dst_path} {video_format=}")
        logger.debug(nicer_args_join(args))
        subprocess.run(args, check=True)
        src_path.unlink()
        tmp_path.replace(dst_path)

    def process_video_dir(
        self,
        video_dir,
        video_id,
        video_filename="video",
        skip_recompress=False,
        **kwargs,
    ):
        files = [
            p
            for p in video_dir.iterdir()
            if p.is_file()
            and p.stem == video_filename
            and p.suffix not in ["png", "jpeg", "jpg", "vtt"]
        ]
        if len(files) == 0:
            logger.error(f"Video file missing in {video_dir} for {video_id}")
            logger.debug(list(video_dir.iterdir()))
            raise FileNotFoundError(f"Missing video file in {video_dir}")
        if len(files) > 1:
            logger.warning(
                f"Multiple video file candidates for {video_id} in {video_dir}. Picking {files[0]} out of {files}"
            )
        src_path = files[0]

        # don't reencode if not requesting recompress and received wanted format
        if skip_recompress or (
            not self.recompress and src_path.suffix[1:] == self.video_format
        ):
            return

        dst_path = src_path.parent.joinpath(f"{video_filename}.{self.video_format}")
        self.recompress_video(src_path, dst_path, **kwargs)
