zimscraperlib
=============

![Build Status](https://github.com/openzim/python_scraperlib/workflows/CI/badge.svg)
[![CodeFactor](https://www.codefactor.io/repository/github/openzim/python_scraperlib/badge)](https://www.codefactor.io/repository/github/openzim/python_scraperlib)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![PyPI version shields.io](https://img.shields.io/pypi/v/zimscraperlib.svg)](https://pypi.org/project/zimscraperlib/)
[![codecov](https://codecov.io/gh/openzim/python_scraperlib/branch/master/graph/badge.svg)](https://codecov.io/gh/openzim/python_scraperlib)

Collection of python code to re-use across python-based scrapers

# Usage

* This library is meant to be installed via PyPI ([`zimscraperlib`](https://pypi.org/project/zimscraperlib/)).
* Make sure to reference it using a version code as the API is subject to frequent changes.
* API should remains the same only within the same *minor* version.

Example usage:

``` pip
zimscraperlib>=1.1,<1.2
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
