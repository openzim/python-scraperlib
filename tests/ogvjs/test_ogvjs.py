#!/usr/bin/env python3
# vim: ai ts=4 sts=4 et sw=4 nu

import shutil
import subprocess
import zipfile

import pytest

from zimscraperlib.download import save_large_file
from zimscraperlib.fix_ogvjs_dist import run


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
def test_ogvjs_installed_script_missing_param():
    # run from installed script to check real conditions
    script = subprocess.run(
        ["/usr/bin/env", "fix_ogvjs_dist"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert script.returncode == 1
    assert script.stdout.strip().startswith("Usage: ")


def test_ogvjs_from_code_missing_params():
    # run from code to mesure coverage easily

    assert run(["fix_ogvjs_dist"]) == 1


@pytest.mark.slow
@pytest.mark.installed
def test_ogvjs_installed_script_ok(tmp_path, videojs_url, ogvjs_url, videojs_ogvjs_url):
    # run from installed script to check real conditions

    prepare_ogvjs_folder(tmp_path, videojs_url, ogvjs_url, videojs_ogvjs_url)

    script = subprocess.run(
        ["/usr/bin/env", "fix_ogvjs_dist", str(tmp_path)],
        text=True,
        capture_output=True,
        check=False,
    )
    assert script.returncode == 0

    with open(tmp_path / "videojs-ogvjs.js") as fh:
        assert "webm" in fh.read()


@pytest.mark.slow
def test_ogvjs_from_code_ok(tmp_path, videojs_url, ogvjs_url, videojs_ogvjs_url):
    # run from code to mesure coverage easily

    prepare_ogvjs_folder(tmp_path, videojs_url, ogvjs_url, videojs_ogvjs_url)

    assert run(["fix_ogvjs_dist", str(tmp_path)]) == 0

    with open(tmp_path / "videojs-ogvjs.js") as fh:
        assert "webm" in fh.read()
