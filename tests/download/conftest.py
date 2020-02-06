#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import pytest


@pytest.fixture(scope="module")
def valid_http_url():
    return "http://google.com/favicon.ico"


@pytest.fixture(scope="module")
def valid_https_url():
    return "https://www.google.com/favicon.ico"


@pytest.fixture(scope="module")
def invalid_url():
    return "http://nodomain.notld/nofile.noext"
