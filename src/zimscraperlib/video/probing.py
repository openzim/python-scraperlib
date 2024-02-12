#!/usr/bin/env python3
# vim: ai ts=4 sts=4 et sw=4 nu


import subprocess


def get_media_info(src_path):
    """dict of file's details from ffprobe

    codecs: list of codecs in use
    duration: file duration in seconds
    bitrate: file's main bitrate"""

    args = [
        "/usr/bin/env",
        "ffprobe",
        "-i",
        f"file:{src_path}",
        "-show_entries",
        "stream=codec_name",
        "-show_entries",
        "format=duration,bit_rate",
        "-v",
        "quiet",
        "-of",
        "csv",
    ]
    ffprobe = subprocess.run(
        args,
        capture_output=True,
        text=True,
        check=False,
    )
    result = ffprobe.stdout.strip().split("\n")
    streams = result[:-1]
    codecs = [stream.split(",")[-1] for stream in streams]
    format_info = result[-1].split(",")[1:]
    return {
        "codecs": codecs,
        "duration": int(format_info[0].split(".")[0]),
        "bitrate": int(format_info[1]),
    }
