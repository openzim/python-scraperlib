#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

""" presets for ImageOptimizer in zimscraperlib.image.optimization module """


class WebpLow:
    """ Low quality WebP image

        Lossy compression
        Low quality (Pillow quality is 40)
        Quality/Speed tradeoff is High """

    VERSION = 1

    options = {
        "lossless": False,
        "quality": 40,
        "method": 6,
    }


class WebpHigh:
    """ High quality WebP image

        Lossy compression
        High quality (Pillow quality is 65)
        Quality/Speed tradeoff is High """

    VERSION = 1

    options = {
        "lossless": False,
        "quality": 65,
        "method": 6,
    }


class GifLow:
    """ Low quality GIF image

        Strongest optimization level
        Colors limited to 256
        High Lossiness
        No extensions in GIF
        Interlaced frames """

    VERSION = 1

    options = {
        "optimize_level": 3,
        "max_colors": 256,
        "lossiness": 90,
        "no_extensions": True,
        "interlace": True,
    }


class GifHigh:
    """ High quality GIF image

        Weak optimization level
        Colors not limited
        Moderate lossiness
        No extensions in GIF
        Interlaced frames """

    VERSION = 1

    options = {
        "optimize_level": 1,
        "lossiness": 50,
        "no_extensions": True,
        "interlace": True,
    }


class PngLow:
    """ Low quality PNG image

        Reduce colors to 256
        Slower and better compression """

    VERSION = 1

    options = {
        "reduce_colors": True,
        "remove_transparency": False,
        "max_colors": 256,
        "fast_mode": False,
    }


class PngHigh:
    """ High quality PNG image

        Do not reduce colors
        Weaker and faster compression """

    VERSION = 1

    options = {
        "reduce_colors": False,
        "remove_transparency": False,
        "fast_mode": True,
    }


class JpegLow:
    """ Low quality JPEG image

        Low quality (40)
        Strip out exif data
        Slower and better compression """

    VERSION = 1

    options = {
        "quality": 40,
        "keep_exif": False,
        "fast_mode": False,
    }


class JpegHigh:
    """ High quality JPEG image

        High quality (70)
        Strip out exif data
        Weaker and faster compression """

    VERSION = 1

    options = {
        "quality": 70,
        "keep_exif": False,
        "fast_mode": True,
    }
