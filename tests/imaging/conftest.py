#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import pathlib

import pytest


def src_image(fname):
    return pathlib.Path(__file__).parent.joinpath(fname)


@pytest.fixture(scope="module")
def png_image():
    return src_image("commons.png")


@pytest.fixture(scope="module")
def jpg_image():
    return src_image("pluto.jpg")


@pytest.fixture(scope="module")
def square_png_image():
    return src_image("square.png")


@pytest.fixture(scope="module")
def square_jpg_image():
    return src_image("square.jpg")
