from __future__ import annotations

import sys
from pathlib import Path

from zimscraperlib import logger
from zimscraperlib.video import presets, reencode


def encode_video(src_path: Path, dst_path: Path, preset: str):
    if not src_path.exists():
        raise ValueError(f"{src_path} does not exists")
    try:
        preset_cls = getattr(presets, preset)
    except AttributeError:
        logger.error(f"{preset} preset not found")
        raise
    logger.info(f"Encoding video {src_path} with {preset} version {preset_cls.VERSION}")
    success, process = reencode(
        src_path=src_path,
        dst_path=dst_path,
        ffmpeg_args=preset_cls().to_ffmpeg_args(),
        with_process=True,
    )  # pyright: ignore[reportGeneralTypeIssues] (returned type is variable, depending on `with_process` value)
    if not success:
        logger.error(f"conversion failed:\n{process.stdout}")


def run(args: list[str] = sys.argv):
    if len(args) < 4:  # noqa: PLR2004
        print(f"Usage: {args[0]} <src_path> <dst_path> <preset>")  # noqa: T201
        print(  # noqa: T201
            "\t<src_path>\tpath to the video to encode."
            "\t<dst_path>\tpath to the store the reencoded video."
            "\t<preset>\tname of preset to use."
        )
        return 1
    encode_video(Path(args[1]), Path(args[2]), args[3])
    return 0


if __name__ == "__main__":
    sys.exit(run())
