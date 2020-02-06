#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--runslow", action="store_true", default=False, help="run slow tests"
    )
    parser.addoption(
        "--runinstalled",
        action="store_true",
        default=False,
        help="run tests checking for installed features",
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: mark test as slow to run")
    config.addinivalue_line(
        "markers", "installed: mark test as testing installed features"
    )


def pytest_collection_modifyitems(config, items):
    skip_slow = pytest.mark.skip(reason="need --runslow option to run")
    skip_installed = pytest.mark.skip(reason="need --runinstalled option to run")

    for item in items:
        if "installed" in item.keywords and not config.getoption("--runinstalled"):
            item.add_marker(skip_installed)
        if "slow" in item.keywords and not config.getoption("--runslow"):
            item.add_marker(skip_slow)
