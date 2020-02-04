#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import os
import subprocess

import requests

WGET_BINARY = os.getenv("WGET_BINARY", "/usr/bin/wget")


def save_file(url, fpath):
    """ download a binary file from its URL """
    req = requests.get(url)
    req.raise_for_status()
    if not fpath.parent.exists():
        fpath.parent.mkdir(exist_ok=True)
    with open(fpath, "wb") as fp:
        fp.write(req.content)


def save_large_file(url, fpath):
    """ download a binary file from its URL, using wget """
    subprocess.run(
        [
            WGET_BINARY,
            "-t",
            "5",
            "--retry-connrefused",
            "--random-wait",
            "-O",
            str(fpath),
            "-c",
            url,
        ],
        check=True,
    )
