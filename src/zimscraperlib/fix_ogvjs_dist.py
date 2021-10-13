#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu


""" quick script to fix videojs-ogvjs so that it triggers on webm mimetype """

import logging
import pathlib
import sys
from typing import Union

logging.basicConfig(format="%(levelname)s:%(message)s", level=logging.DEBUG)
logger = logging.getLogger(__name__)


def fix_source_dir(source_vendors_path: Union[pathlib.Path, str]):
    """update ogvjs plugin to trigger on webm mimetype"""
    root = pathlib.Path(source_vendors_path)
    logger.info("fixing videosjs-ogvjs.js")
    plugin_path = root.joinpath("videojs-ogvjs.js")
    with open(plugin_path, "r") as fp:
        content = fp.read()

    content = content.replace(
        "return type.indexOf('/ogg') !== -1 ? 'maybe' : '';",
        "return (type.indexOf('/webm') !== -1 || type.indexOf('/ogg') !== -1)"
        " ? 'maybe' : '';",
    )

    with open(plugin_path, "w") as fp:
        fp.write(content)

    logger.info("all done.")


def run():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <source_vendors_path>")
        print(
            "\t<source_vendors_path>\tpath to your folder containing "
            "ogvjs/videojs/videojs-ogvjs."
        )
        sys.exit(1)
    return sys.exit(fix_source_dir(sys.argv[1]))


if __name__ == "__main__":
    run()
