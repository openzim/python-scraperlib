#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import pathlib
from setuptools import setup, find_packages

root_dir = pathlib.Path(__file__).parent


def read(*names, **kwargs):
    with open(root_dir.joinpath(*names), "r") as fh:
        return fh.read()


setup(
    name="zimscraperlib",
    version=read("src", "zimscraperlib", "VERSION").strip(),
    description="Collection of python tools to re-use common code across scrapers",
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    author="kiwix",
    author_email="reg@kiwix.org",
    url="https://github.com/openzim/python-scraperlib",
    keywords="kiwix zim offline",
    license="GPLv3+",
    packages=find_packages("src"),
    package_dir={"": "src"},
    install_requires=[
        line.strip()
        for line in read("requirements.txt").splitlines()
        if not line.strip().startswith("#")
    ],
    setup_requires=["pytest-runner"],
    zip_safe=False,
    include_package_data=True,
    entry_points={
        "console_scripts": ["fix_ogvjs_dist=zimscraperlib.fix_ogvjs_dist:run"]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
    ],
    python_requires=">=3.6",
)
