#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import subprocess

import requests

from . import logger


def save_file(url, fpath, timeout=30, retries=5):
    """download a file from its URL, and return headers

    Only recommended to be used with small files/HTMLs"""

    for left_attempts in range(retries, -1, -1):
        try:
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            with open(fpath, "wb") as fp:
                fp.write(resp.content)
            return resp.headers
        except requests.exceptions.RequestException as exc:
            logger.debug(
                f"Request for {url} failed ({left_attempts} attempts left)\n{exc}"
            )
            if left_attempts == 0:
                raise exc


def save_large_file(url, fpath):
    """ download a binary file from its URL, using wget """
    subprocess.run(
        [
            "/usr/bin/env",
            "wget",
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
