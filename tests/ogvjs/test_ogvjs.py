#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import shutil
import subprocess
import sys
import zipfile

import pytest

from zimscraperlib.download import save_large_file


def prepare_ogvjs_folder(tmp_path, videojs_url, ogvjs_url, videojs_ogvjs_url):
    videojs_zip = tmp_path / "video-js-7.6.4.zip"
    if not videojs_zip.exists():
        save_large_file(videojs_url, videojs_zip)
    videojs_dir = tmp_path.joinpath("videojs")
    shutil.rmtree(videojs_dir, ignore_errors=True)
    videojs_dir.mkdir()
    with zipfile.ZipFile(videojs_zip) as zipf:
        zipf.extractall(videojs_dir)

    ogvjs_zip = tmp_path / "ogvjs-1.6.1.zip"
    if not ogvjs_zip.exists():
        save_large_file(ogvjs_url, ogvjs_zip)
    ogvjs_dir = tmp_path.joinpath("ogvjs")
    ogvjs_dir_tmp = tmp_path.joinpath("ogvjs_tmp")
    shutil.rmtree(ogvjs_dir, ignore_errors=True)
    shutil.rmtree(ogvjs_dir_tmp, ignore_errors=True)
    ogvjs_dir.mkdir()
    with zipfile.ZipFile(ogvjs_zip) as zipf:
        zipf.extractall(ogvjs_dir_tmp)
    # move back one dir
    ogvjs_dir_tmp.joinpath("ogvjs-1.6.1").rename(ogvjs_dir)

    videojs_ogvjs_zip = tmp_path / "v1.3.1.zip"
    if not videojs_ogvjs_zip.exists():
        save_large_file(videojs_ogvjs_url, videojs_ogvjs_zip)
    member = "videojs-ogvjs-1.3.1/dist/videojs-ogvjs.js"
    with zipfile.ZipFile(videojs_ogvjs_zip) as zipf:
        zipf.extract(member, tmp_path)
    # move script to root
    tmp_path.joinpath(member).rename(tmp_path.joinpath("videojs-ogvjs.js"))


@pytest.mark.installed
def test_installed_script():
    kwargs = {"universal_newlines": True, "stdout": subprocess.PIPE}
    script = subprocess.run(["fix_ogvjs_dist"], **kwargs)  # nosec
    assert script.returncode == 1
    assert script.stdout.strip().startswith("Usage: ")


def test_missing_param():
    script = subprocess.run(
        [
            sys.executable,
            "-m",
            "zimscraperlib.fix_ogvjs_dist",
        ]
    )
    assert script.returncode == 1


@pytest.mark.slow
def test_fix_ogvjs_dist(tmp_path, videojs_url, ogvjs_url, videojs_ogvjs_url):
    prepare_ogvjs_folder(tmp_path, videojs_url, ogvjs_url, videojs_ogvjs_url)

    # run to fix it from source (using installed script name)
    script = subprocess.run(
        [
            sys.executable,
            "-m",
            "zimscraperlib.fix_ogvjs_dist",
            str(tmp_path),
        ],
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    assert script.returncode == 0

    with open(tmp_path / "videojs-ogvjs.js", "r") as fh:
        assert "webm" in fh.read()
