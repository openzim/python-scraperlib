zimscraperlib
=============

[![Build Status](https://github.com/openzim/python-scraperlib/workflows/CI/badge.svg?query=branch%3Amain)](https://github.com/openzim/python-scraperlib/actions?query=branch%3Amain)
[![CodeFactor](https://www.codefactor.io/repository/github/openzim/python-scraperlib/badge)](https://www.codefactor.io/repository/github/openzim/python-scraperlib)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![PyPI version shields.io](https://img.shields.io/pypi/v/zimscraperlib.svg)](https://pypi.org/project/zimscraperlib/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/zimscraperlib.svg)](https://pypi.org/project/zimscraperlib)
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

## Alpine
```
apk add ffmpeg gifsicle libmagic wget libjpeg
```

**Nota:** i18n features do not work on Alpine, see https://github.com/openzim/python-scraperlib/issues/134 ; there is one corresponding test which is failing.

# Contribution

This project adheres to openZIM's [Contribution Guidelines](https://github.com/openzim/overview/wiki/Contributing).

This project has implemented openZIM's [Python bootstrap, conventions and policies](https://github.com/openzim/_python-bootstrap/docs/Policy.md) **v1.0.2**.

```shell
pip install hatch
pip install ".[dev]"
pre-commit install
# For tests
invoke coverage
```

# Users

Non-exhaustive list of scrapers using it (check status when updating API):

* [openzim/freecodecamp](https://github.com/openzim/freecodecamp)
* [openzim/gutenberg](https://github.com/openzim/gutenberg)
* [openzim/ifixit](https://github.com/openzim/ifixit)
* [openzim/kolibri](https://github.com/openzim/kolibri)
* [openzim/nautilus](https://github.com/openzim/nautilus)
* [openzim/nautilus](https://github.com/openzim/nautilus)
* [openzim/openedx](https://github.com/openzim/openedx)
* [openzim/sotoki](https://github.com/openzim/sotoki)
* [openzim/ted](https://github.com/openzim/ted)
* [openzim/warc2zim](https://github.com/openzim/warc2zim)
* [openzim/wikihow](https://github.com/openzim/wikihow)
* [openzim/youtube](https://github.com/openzim/youtube)
