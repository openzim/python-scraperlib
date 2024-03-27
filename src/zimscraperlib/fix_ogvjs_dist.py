#!/usr/bin/env python3
# vim: ai ts=4 sts=4 et sw=4 nu


""" quick script to fix videojs-ogvjs so that it triggers on webm mimetype """

from __future__ import annotations

import logging
import pathlib
import sys

logging.basicConfig(format="%(levelname)s:%(message)s", level=logging.DEBUG)
logger = logging.getLogger(__name__)


def fix_source_dir(source_vendors_path: pathlib.Path | str):
    """update ogvjs plugin to trigger on webm mimetype"""
    root = pathlib.Path(source_vendors_path)
    logger.info("fixing videosjs-ogvjs.js")
    plugin_path = root.joinpath("videojs-ogvjs.js")
    with open(plugin_path) as fp:
        content = fp.read()

    content = content.replace(
        "return type.indexOf('/ogg') !== -1 ? 'maybe' : '';",
        "return (type.indexOf('/webm') !== -1 || type.indexOf('/ogg') !== -1)"
        " ? 'maybe' : '';",
    )

    with open(plugin_path, "w") as fp:
        fp.write(content)

    logger.info("all done.")


def run(args: list[str] = sys.argv):
    if len(args) < 2:  # noqa: PLR2004
        print(f"Usage: {args[0]} <source_vendors_path>")  # noqa: T201
        print(  # noqa: T201
            "\t<source_vendors_path>\tpath to your folder containing "
            "ogvjs/videojs/videojs-ogvjs."
        )
        return 1
    fix_source_dir(args[1])
    return 0


if __name__ == "__main__":
    sys.exit(run())
