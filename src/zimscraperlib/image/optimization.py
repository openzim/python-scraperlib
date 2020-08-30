#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

""" An image optimization module to optimize the following image formats:

    - JPEG (using optimize-images)
    - PNG (using optimize-images)
    - GIF (using gifsicle with lossy optimization)
    - WebP (using Pillow)

    The following options are available to tune in for each of the formats -

    JPEG:
        quality: JPEG quality (integer between 1 and 100)
            values: 50 | 55 | 35 | 100 | XX
        keep_exif: Whether to keep EXIF data in JPEG (boolean)
            values: True | False
        grayscale: Whether to convert image to grayscale (boolean)
            values: True | False
        fast_mode: Whether to use faster but weaker compression (boolean)
            values: True | False

    PNG:
        remove_transparency: Whether to remove transparency (boolean)
            values: True | False
        reduce_colors: Whether to reduce colors using adaptive color pallette (boolean)
            values: True | False
        max_colors: Maximum number of colors if reduce_colors is True (integer between 1 and 256)
            values: 35 | 64 | 256 | 128 | XX
        background_color: Background color if remove_transparency is True (tuple containing RGB values)
            values: (255, 255, 255) | (221, 121, 108) | (XX, YY, ZZ)
        fast_mode: Whether to use faster but weaker compression (boolean)
            values: True | False

    WebP (refer to the link for more details - https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#webp):
        lossless: Whether to use lossless compression (boolean)
            values: True | False
        quality: WebP quality for lossy, effort put into compression for lossless (integer between 0 to 100)
            values: 30 | 45 | 100 | XX
        method: Quality/speed trade-off; higher values give better compression (integer between 1 and 6)
            values: 1 | 2 | 3 | 4 | 5 | 6 

    GIF (refer to the link for more details - https://www.lcdf.org/gifsicle/man.html):
        optimize_level: Optimization level; higher values give better compression (integer between 1 and 3)
            values: 1 | 2 | 3
        lossiness: Level of lossy optimization to use; higher values give better compression (integer)
            values: 20 | 45 | 80 | XX
        interlace: Whether to interlace the frames (boolean)
            values: True | False
        no_extensions: Whether to remove all extension options from GIF (boolean)
            values: True | False
        max_colors: Maximum number of colors in the resultant GIF (integer between 2 and 256)
            values: 2 | 86 | 128 | 256 | XX

    Some important notes: 
    - This makes use of the --lossy option from gifsicle which is present only in versions above 1.92.
      If the package manager has a lower version, you can build gifsicle from source and install or
      do not use the lossiness option.

    - The ImageOptimizer class takes a dict consisting the aforementioned options and values while initialization.
      A dict in the same format can also be passed to other methods via the override_options argument to override any
      option set while initlization. Presets for the optimizer are available in zimscraperlib.image.presets.

    - If no options for an image format is passed, the optimizer can still run on default settings which give
      a bit less size than the original images (probably a balance between the High and Low presets). """

import shutil
import tempfile
import pathlib
import subprocess
from typing import Optional

from PIL import Image
from optimize_images.data_structures import Task
from optimize_images.do_optimization import do_optimization

from . import save_image
from .. import logger
from ..logging import nicer_args_join


class ImageOptimizer:
    """ ImageOptimizer class to optimize various images using various optimizers """

    def __init__(
        self,
        png_options: Optional[dict] = {},
        jpeg_options: Optional[dict] = {},
        webp_options: Optional[dict] = {},
        gif_options: Optional[dict] = {},
    ) -> None:
        self.png_options = png_options
        self.jpeg_options = jpeg_options
        self.gif_options = gif_options
        self.webp_options = webp_options

    def optimize_png_jpg(
        self,
        src: pathlib.Path,
        dst: pathlib.Path,
        image_format: str,
        override_options: dict,
    ) -> bool:

        """ method to optimize PNG or JPEG files using a pure python external optimizer """

        # use a temporary file as source as optimization is done destructively
        tmp_fh = tempfile.NamedTemporaryFile(delete=False, suffix=src.suffix)
        tmp_fh.close()
        tmp_path = pathlib.Path(tmp_fh.name)
        shutil.copy(src, tmp_path)

        # generate task for optimize_images

        # max_w and max_h is 0 because we have a better image resizing function in scraperlib already
        # remove_transparency, reduce_colors, max_colors, convert_all, conv_big, bg_color, force_del, are specific to PNG
        # quality, keep_exif are specific to JPEG
        if image_format == "jpg":
            # generate options for jpeg
            optimization_task = Task(
                src_path=str(tmp_path.resolve()),
                quality=override_options.get(
                    "quality", self.jpeg_options.get("quality", 50)
                ),
                remove_transparency=False,
                reduce_colors=False,
                max_colors=256,
                max_w=0,
                max_h=0,
                keep_exif=override_options.get(
                    "keep_exif", self.jpeg_options.get("keep_exif", False)
                ),
                convert_all=False,
                conv_big=False,
                force_del=False,
                bg_color=(255, 255, 255),
                grayscale=override_options.get(
                    "grayscale", self.jpeg_options.get("grayscale", False)
                ),
                no_size_comparison=True,
                fast_mode=override_options.get(
                    "fast_mode", self.jpeg_options.get("fast_mode", False)
                ),
            )
        else:
            # generate options for png

            # convert_all converts all PNG to JPEG, hence set to False
            # conv_big converts big PNG images to JPEG, hence set to False
            # force_del deletes the original PNG after convertion to JPEG if the above two options are used, so kept False
            optimization_task = Task(
                src_path=str(tmp_path.resolve()),
                quality=90,
                remove_transparency=override_options.get(
                    "remove_transparency",
                    self.png_options.get("remove_transparency", False),
                ),
                reduce_colors=override_options.get(
                    "reduce_colors", self.png_options.get("reduce_colors", True)
                ),
                max_colors=override_options.get(
                    "max_colors", self.png_options.get("max_colors", 256)
                ),
                max_w=0,
                max_h=0,
                keep_exif=False,
                convert_all=False,
                conv_big=False,
                force_del=False,
                bg_color=override_options.get(
                    "background_color",
                    self.png_options.get("background_color", (255, 255, 255)),
                ),
                grayscale=override_options.get(
                    "grayscale", self.png_options.get("grayscale", False)
                ),
                no_size_comparison=True,
                fast_mode=override_options.get(
                    "fast_mode", self.png_options.get("fast_mode", False)
                ),
            )

        # optimize the image
        result = do_optimization(optimization_task)
        if result.was_optimized:
            logger.info(f"Successfully optimized image: {src}")
            logger.debug(f"Space savings: {result.orig_size - result.final_size}")
            shutil.copy(tmp_path, dst)
            tmp_path.unlink()
        return result.was_optimized

    def optimize_webp(
        self, src: pathlib.Path, dst: pathlib.Path, override_options: dict
    ) -> bool:
        """ method to optimize WebP using Pillow options """

        lossless = override_options.get(
            "lossless", self.webp_options.get("lossless", None)
        )
        quality = override_options.get(
            "quality", self.webp_options.get("quality", None)
        )
        method = override_options.get("method", self.webp_options.get("method", None))
        webp_image = Image.open(src)
        params = {
            "lossless": lossless if lossless is not None else False,
            "quality": quality if quality is not None else 55,
            "method": method if method is not None else 5,
        }
        save_image(webp_image, dst, fmt="WEBP", **params)
        return True

    def optimize_gif(
        self, src: pathlib.Path, dst: pathlib.Path, override_options: dict
    ) -> bool:
        """ method to optimize GIFs using gifsicle >= 1.92 """

        optimize_level = override_options.get(
            "optimize_level", self.gif_options.get("optimize_level", None)
        )
        max_colors = override_options.get(
            "max_colors", self.gif_options.get("max_colors", None)
        )
        lossiness = override_options.get(
            "lossiness", self.gif_options.get("lossiness", None)
        )
        no_extensions = override_options.get(
            "no_extensions", self.gif_options.get("no_extensions", None)
        )
        interlace = override_options.get(
            "interlace", self.gif_options.get("interlace", None)
        )
        # use gifsicle
        args = ["gifsicle"]
        if optimize_level:
            args += [f"-O{optimize_level}"]
        if max_colors:
            args += ["--colors", str(max_colors)]
        if lossiness:
            args += [f"--lossy={lossiness}"]
        if no_extensions:
            args += ["--no-extensions"]
        if interlace:
            args += ["--interlace"]
        args += [str(src)]
        logger.debug(nicer_args_join(args))
        with open(dst, "w") as out_file:
            gifsicle = subprocess.run(args, stdout=out_file)
        gifsicle.check_returncode()
        return True

    def optimize_image(
        self,
        src: pathlib.Path,
        dst: pathlib.Path,
        delete_src: Optional[bool] = True,
        png_override_options: Optional[dict] = {},
        jpeg_override_options: Optional[dict] = {},
        gif_override_options: Optional[dict] = {},
        webp_override_options: Optional[dict] = {},
    ) -> None:
        """ method to select optimizer and optimize images based on extension """

        # check if file is present
        if not src.is_file():
            raise FileNotFoundError("The requested image is not present")
        optimized = False

        # check extension and optimize
        if src.suffix in [".jpeg", ".jpg"]:
            optimized = self.optimize_png_jpg(
                src, dst, image_format="jpg", override_options=jpeg_override_options
            )
        elif src.suffix == ".png":
            optimized = self.optimize_png_jpg(
                src, dst, image_format="png", override_options=png_override_options
            )
        elif src.suffix == ".webp":
            optimized = self.optimize_webp(
                src, dst, override_options=webp_override_options
            )
        elif src.suffix == ".gif":
            optimized = self.optimize_gif(
                src, dst, override_options=gif_override_options
            )
        else:
            raise Exception("File not supported for optimization as an image")

        # delete src image if requested
        if src.resolve() != dst.resolve() and src.exists() and delete_src and optimized:
            src.unlink()
