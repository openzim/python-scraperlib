zimscraperlib
=============

[![Build Status](https://github.com/openzim/python-scraperlib/workflows/CI/badge.svg?query=branch%3Amaster)](https://github.com/openzim/python-scraperlib/actions?query=branch%3Amaster)
[![CodeFactor](https://www.codefactor.io/repository/github/openzim/python-scraperlib/badge)](https://www.codefactor.io/repository/github/openzim/python-scraperlib)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![PyPI version shields.io](https://img.shields.io/pypi/v/zimscraperlib.svg)](https://pypi.org/project/zimscraperlib/)
[![codecov](https://codecov.io/gh/openzim/python-scraperlib/branch/master/graph/badge.svg)](https://codecov.io/gh/openzim/python-scraperlib)

Collection of python code to re-use across python-based scrapers

# Usage

* This library is meant to be installed via PyPI ([`zimscraperlib`](https://pypi.org/project/zimscraperlib/)).
* Make sure to reference it using a version code as the API is subject to frequent changes.
* API should remain the same only within the same *minor* version.

Example usage:

``` pip
zimscraperlib>=1.1,<1.2
```

# Dependencies

* libmagic
* wget
* libzim (auto-installed, not available on Windows)
* Pillow
* FFmpeg
* gifsicle (>=1.92)

## macOS

```sh
brew install libmagic wget libtiff libjpeg webp little-cms2 ffmpeg gifsicle
```

## Linux

```sh
sudo apt install libmagic1 wget ffmpeg \
    libtiff5-dev libjpeg8-dev libopenjp2-7-dev zlib1g-dev \
    libfreetype6-dev liblcms2-dev libwebp-dev tcl8.6-dev tk8.6-dev python3-tk \
    libharfbuzz-dev libfribidi-dev libxcb1-dev gifsicle
```

# Users

Non-exhaustive list of scrapers using it (check status when updating API):

* [openzim/youtube](https://github.com/openzim/youtube)
* [openzim/nautilus](https://github.com/openzim/nautilus)

# releasing

* Update your dependencies: `pip install -U setuptools wheel twine`
* Make sure CHANGELOG.md is up-to-date
* Bump version on `src/zimscraperlib/VERSION`
* Build packages `python ./setup.py sdist bdist_wheel`
* Upload to PyPI `twine upload dist/zimscraperlib-2.0.0*`.
* Commit your Changelog + version bump changes
* Tag version on git `git tag -a v2.0.0`
