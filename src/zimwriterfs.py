#!/usr/bin/env python3

""" zimwriterfs alternative implementation

    requires libmagic1 and zimscraperlib (python)

    WARN: the following zimwriterfs features are not implemented:
        `--inflateHtml`
        `--skip-libmagic-check`
"""

from __future__ import annotations

import argparse
import datetime
import logging
from pathlib import Path

from zimscraperlib.__about__ import __version__
from zimscraperlib.constants import (
    MAXIMUM_DESCRIPTION_METADATA_LENGTH,
    MAXIMUM_LONG_DESCRIPTION_METADATA_LENGTH,
    RECOMMENDED_MAX_TITLE_LENGTH,
)
from zimscraperlib.logging import getLogger
from zimscraperlib.zim.creator import Creator
from zimscraperlib.zim.filesystem import add_redirects_to_zim, add_to_zim

SCRAPER = f"zimwriterfs(py) {__version__}"
logger = getLogger("zimwriterfs", level=logging.INFO)


def main(
    *,
    src_dir: str,
    dst_path: str,
    name: str,
    language: str,
    title: str,
    description: str,
    creator: str,
    publisher: str,
    illus_fname: str,
    tags: str,
    welcome: str,
    verbose: bool,
    threads: int,
    without_ft_index: bool,
    redirects_path: str | None = None,
    long_description: str | None = None,
    flavour: str | None = None,
    source: str | None = None,
    scraper: str | None = None,
    license_m: str | None = None,
    relation: str | None = None,
    cluster_size: int | None = None,
):
    if verbose:
        logger = getLogger("zimwriterfs", level=logging.DEBUG)

    logger.info(f"Dumping {src_dir} into {dst_path}")

    build_dir = Path(src_dir).expanduser().resolve()
    if not build_dir.exists() or not build_dir.is_dir():
        raise OSError(f"Incorrect build_dir: {build_dir}")

    illustration_fpath = build_dir / illus_fname
    if not illustration_fpath.exists() or not illustration_fpath.is_file():
        raise OSError(f"Incorrect illustration: {illus_fname} ({illustration_fpath})")
    with open(illustration_fpath, "rb") as fh:
        illustration_data = fh.read()

    redirects_fpath = Path(redirects_path) if redirects_path else None

    zim_file = (
        Creator(
            filename=Path(dst_path).expanduser().resolve(),
            main_path=welcome,
            ignore_duplicates=False,
            disable_metadata_checks=False,
        )
        .config_indexing(not without_ft_index, language)
        .config_verbose(verbose)
        .config_nbworkers(threads)
    )

    if cluster_size:
        zim_file.config_clustersize(cluster_size)

    zim_file.config_metadata(
        Name=name,
        Language=language,
        Title=title,
        Description=description,
        LongDescription=long_description,
        Creator=creator,
        Publisher=publisher,
        Date=datetime.date.today(),  # noqa: DTZ011
        Illustration_48x48_at_1=illustration_data,
        Tags=";".join(tags.split(";")) if tags else None,
        Scraper=scraper,
        Flavour=flavour,
        Source=source,
        License=license_m,
        Relation=relation,
    )

    zim_file.start()
    try:
        logger.debug(f"Preparing zimfile at {zim_file.filename}")

        # recursively add content from build_dir
        logger.debug(f"Recursively adding files from {build_dir}")
        add_to_zim(build_dir, zim_file, build_dir)

        if redirects_fpath:
            logger.debug("Creating redirects")
            add_redirects_to_zim(zim_file, redirects_file=redirects_fpath)

    # prevents .finish() which would create an incomplete .zim file
    # this would leave a .zim.tmp folder behind.
    # UPSTREAM: wait until a proper cancel() is provided
    except Exception:
        zim_file.can_finish = False  # pragma: no cover
        raise
    finally:
        zim_file.finish()


def entrypoint():
    parser = argparse.ArgumentParser(
        prog="zimwriterfs",
        description="Create a ZIM file off a directory containing a static website",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Notes:
    - openZIM Metadata: https://wiki.openzim.org/wiki/Metadata
    - Set `ZIMSCRAPERLIB_DEBUG=1` environ to see all files included in ZIM""",
    )

    parser.add_argument("src_dir")
    parser.add_argument("dst_path")

    parser.add_argument(
        "-V",
        "--version",
        help="Display version and exit",
        action="version",
        version=SCRAPER,
    )

    parser.add_argument(
        "-n",
        "--name",
        help="Human identifier for the content (see spec)",
        required=True,
    )

    parser.add_argument(
        "-t",
        "--title",
        help=f"Title of the content ({RECOMMENDED_MAX_TITLE_LENGTH} chars max)",
        required=True,
    )

    parser.add_argument(
        "-l",
        "--language",
        help="ISO-639-3 Language code of the content",
        required=True,
    )

    parser.add_argument(
        "-d",
        "--description",
        help="Description of the content "
        f"({MAXIMUM_DESCRIPTION_METADATA_LENGTH} chars max)",
        required=True,
    )

    parser.add_argument(
        "-w",
        "--welcome",
        help="Relative path to home/main page (ex: `home.html`)",
        required=True,
    )

    parser.add_argument(
        "-I",
        "--illustration",
        dest="illus_fname",
        help="Relative path to the ZIM's illustration. Must be a 48x48px PNG",
        required=True,
    )

    parser.add_argument(
        "-c",
        "--creator",
        help="Creator of the Content",
        required=True,
    )

    parser.add_argument(
        "-p",
        "--publisher",
        help="Publisher of the Content",
        required=True,
    )

    parser.add_argument(
        "-r",
        "--redirects",
        dest="redirects_path",
        help="Path to a TSV file containing a list of redirects (url title target_url)",
        required=False,
    )

    parser.add_argument(
        "-a",
        "--tags",
        help="ZIM Tags, semicolon separated",
        default="",
        required=False,
    )

    parser.add_argument(
        "-e",
        "--source",
        help="Content source URL",
        required=False,
    )

    parser.add_argument(
        "-o",
        "--flavour",
        help="custom (version independent) content flavour",
        required=False,
    )

    parser.add_argument(
        "-s",
        "--scraper",
        help="custom (version independent) content flavour",
        default=SCRAPER,
        required=False,
    )

    parser.add_argument(
        "--license",
        help="License of the content",
        dest="license_m",
        required=False,
    )

    parser.add_argument(
        "--relation",
        help="URI of external related ressources ",
        required=False,
    )

    parser.add_argument(
        "-L",
        "--longDescription",
        dest="long_description",
        help="Longer description of the content "
        f"({MAXIMUM_LONG_DESCRIPTION_METADATA_LENGTH} chars max)",
        required=False,
    )

    parser.add_argument(
        "-v",
        "--verbose",
        help="Whether to display processing details",
        action="store_true",
        default=False,
        required=False,
    )

    parser.add_argument(
        "-m",
        "--clusterSize",
        dest="cluster_size",
        type=int,
        help="Number of bytes per ZIM cluster (libzim defaults to 2MiB)",
        default=None,
        required=False,
    )

    parser.add_argument(
        "-J",
        "--threads",
        type=int,
        default=4,
        help="Number of threads/workers for libzim to use",
        required=False,
    )

    parser.add_argument(
        "-j",
        "--withoutFTIndex",
        dest="without_ft_index",
        action="store_true",
        default=False,
        help="Don't create and add a fulltext index of the content to the ZIM",
        required=False,
    )

    # parser.add_argument(
    #     "-x",
    #     "--inflateHtml",
    #     dest="inflate_html",
    #     action="store_true",
    #     default=False,
    #     help="[NOT IMPLEMENTED] try to inflate HTML files before packing",
    #     required=False,
    # )

    # parser.add_argument(
    #     "--skip-libmagic-check",
    #     dest="skip_libmagic_check",
    #     action="store_true",
    #     default=False,
    #     help="Accept to run even if magic file cannot be loaded "
    #     + "(mimetypes in the zim file may be wrong)",
    #     required=False,
    # )

    args = parser.parse_args()

    try:
        main(**dict(args._get_kwargs()))
    except Exception as exc:
        logger.exception(exc)
        logger.error(f"FAILED. An error occured: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    entrypoint()
