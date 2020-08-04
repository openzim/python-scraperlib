#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import shutil

from optimize_images.data_structures import Task
from optimize_images.do_optimization import do_optimization

from .. import logger


class ImageOptimizer:
    def __init__(self, png_options=None, jpeg_options=None):
        self.png_options = png_options
        self.jpeg_options = jpeg_options

    def optimize_png_jpeg(self, src, dst, format, override_options={}):
        # generate task for optimize_images
        if format == "jpeg":
            # generate options for jpeg
            optimization_task = Task(
                str(src.resolve()),
                override_options.get("quality", self.jpeg_options.get("quality", 90)),
                False,
                False,
                255,
                0,
                0,
                override_options.get(
                    "keep_exif", self.jpeg_options.get("keep_exif", False)
                ),
                False,
                False,
                False,
                (255, 255, 255),
                grayscale=override_options.get(
                    "grayscale", self.jpeg_options.get("grayscale", False)
                ),
                ignore_size_comparison=True,
                fast_mode=override_options.get(
                    "fast_mode", self.jpeg_options.get("fast_mode", False)
                ),
            )
        else:
            # generate options for png
            optimization_task = Task(
                str(src.resolve()),
                90,
                override_options.get(
                    "remove_transparency",
                    self.png_options.get("remove_transparency", False),
                ),
                override_options.get(
                    "reduce_colors", self.png_options.get("reduce_colors", False)
                ),
                override_options.get(
                    "max_colors", self.png_options.get("max_colors", 255)
                ),
                0,
                0,
                False,
                False,
                False,
                False,
                override_options.get(
                    "background_color",
                    self.png_options.get("background_color", (255, 255, 255)),
                ),
                grayscale=override_options.get(
                    "grayscale", self.png_options.get("grayscale", False)
                ),
                ignore_size_comparison=True,
                fast_mode=override_options.get(
                    "fast_mode", self.png_options.get("fast_mode", False)
                ),
            )

        # optimize the image
        result = do_optimization(optimization_task)
        if result.was_optimized:
            logger.info(f"Successfully optimized image: {src}")
            logger.debug(f"Space savings: {result.orig_size - result.final_size}")
        else:
            logger.warning(f"{src} not optimized")
        if src.resolve() != dst.resolve():
            logger.info(f"Copying {src} to {dst}")
            shutil.copy2(src, dst)

    def optimize_image(self, src, dst, delete_src=True):
        # optimize the image with the correct optimizer
        if not src.is_file():
            raise FileNotFoundError("The requested image is not present")
        if src.suffix in [".jpeg", ".jpg"]:
            self.optimize_png_jpeg(src, dst, format="jpeg")
        elif src.suffix == ".png":
            self.optimize_png_jpeg(src, dst, format="png")
        else:
            logger.error("Image format not supported for optimization")
            return
        if src.resolve() != dst.resolve() and src.exists() and delete_src:
            src.unlink()
