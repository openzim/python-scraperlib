# zimscraperlib

[![Build Status](https://github.com/openzim/python-scraperlib/workflows/CI/badge.svg?query=branch%3Amain)](https://github.com/openzim/python-scraperlib/actions?query=branch%3Amain)
[![CodeFactor](https://www.codefactor.io/repository/github/openzim/python-scraperlib/badge)](https://www.codefactor.io/repository/github/openzim/python-scraperlib)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![PyPI version shields.io](https://img.shields.io/pypi/v/zimscraperlib.svg)](https://pypi.org/project/zimscraperlib/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/zimscraperlib.svg)](https://pypi.org/project/zimscraperlib)
[![codecov](https://codecov.io/gh/openzim/python-scraperlib/branch/master/graph/badge.svg)](https://codecov.io/gh/openzim/python-scraperlib)
[![Read the Docs](https://img.shields.io/readthedocs/python-scraperlib)](https://python-scraperlib.readthedocs.io/)

Collection of python code to re-use across python-based scrapers

# Usage

- This library is meant to be installed via PyPI ([`zimscraperlib`](https://pypi.org/project/zimscraperlib/)).
- Make sure to reference it using a version code as the API is subject to frequent changes.
- API should remain the same only within the same _minor_ version.

Example usage:

```pip
zimscraperlib>=1.1,<1.2
```

See documentation at [Read the Docs](https://python-scraperlib.readthedocs.io/) for details.

> [!WARNING]
> While this library brings support for downloading videos with yt-dlp, recent changes in Youtube have forced yt-dlp team
> to require new dependencies for youtube videos (see https://github.com/yt-dlp/yt-dlp/issues/15012). These dependencies
> are significantly big and not needed for all other backend supported by yt-dlp (only youtube needs it). These dependencies
> are hence not included in this library dependencies (yet, see https://github.com/openzim/python-scraperlib/issues/268),
> you have to install them on your own if you intend to download videos from Youtube.

# Dependencies

Most dependencies are installed automatically by pip (from PyPI by default). The following system packages may be required depending on which features you use:

- **libmagic** — required for file type detection (used in most scrapers)
- **wget** — required only for `zimscraperlib.download` functions
- **FFmpeg** — required only for video processing functions
- **gifsicle** (>=1.92) — required only for GIF optimization
- **libcairo** — required only for SVG-to-PNG conversion
- **libzim** — auto-installed via PyPI, not available on Windows
- **Pillow** — auto-installed via PyPI; pre-built wheels are used by default and no system image libraries are needed. Only if you need to build Pillow from source should you install additional system libraries — see [Pillow's build documentation](https://pillow.readthedocs.io/en/latest/installation/building-from-source.html) for details.
  > **Note:** To run the full test suite, all system dependencies listed above must be installed.

## macOS

```sh
brew install libmagic wget ffmpeg gifsicle cairo
```

## Linux

```sh
sudo apt install libmagic1 wget ffmpeg gifsicle libcairo2
```

## Alpine

```sh
apk add ffmpeg gifsicle libmagic wget cairo
```

# Contribution

This project adheres to openZIM's [Contribution Guidelines](https://github.com/openzim/overview/wiki/Contributing).

This project has implemented openZIM's [Python bootstrap, conventions and policies](https://github.com/openzim/_python-bootstrap/docs/Policy.md) **v1.0.2**.

All instructions below must be run from the root of your local clone of this repository.

If you do not already have it on your system, install [hatch](https://hatch.pypa.io/latest/install/):

```shell
pip install hatch
```

Start a hatch shell — this will install all dependencies including dev in an isolated virtual environment:

```shell
hatch shell
```

Set up the pre-commit Git hook (runs linters automatically before each commit):

```shell
pre-commit install
```

Run tests with coverage:

```shell
invoke coverage
```

# Users

Non-exhaustive list of scrapers using it (check status when updating API):

- [openzim/freecodecamp](https://github.com/openzim/freecodecamp)
- [openzim/gutenberg](https://github.com/openzim/gutenberg)
- [openzim/ifixit](https://github.com/openzim/ifixit)
- [openzim/kolibri](https://github.com/openzim/kolibri)
- [openzim/nautilus](https://github.com/openzim/nautilus)
- [openzim/nautilus](https://github.com/openzim/nautilus)
- [openzim/openedx](https://github.com/openzim/openedx)
- [openzim/sotoki](https://github.com/openzim/sotoki)
- [openzim/ted](https://github.com/openzim/ted)
- [openzim/warc2zim](https://github.com/openzim/warc2zim)
- [openzim/wikihow](https://github.com/openzim/wikihow)
- [openzim/youtube](https://github.com/openzim/youtube)
