#!/usr/bin/env python3
# vim: ai ts=4 sts=4 et sw=4 nu

import io
import uuid

import pytest


@pytest.fixture(scope="function")
def random_id():
    return uuid.uuid4().hex


@pytest.fixture(scope="function")
def console():
    return io.StringIO()
