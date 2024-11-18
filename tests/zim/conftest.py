import base64
import datetime
import pathlib
from typing import Any, NamedTuple

import pytest

from zimscraperlib.zim.metadata import (
    DEFAULT_DEV_ZIM_METADATA,
    MANDATORY_ZIM_METADATA_KEYS,
)


@pytest.fixture(scope="function")
def html_str():
    """sample HTML content with various links"""
    return """<html>
<body>
<ul>
    <li><a href="download/toto.pdf">PDF doc</a></li>
    <li><a href="download/toto.txt">text file</a></li>
    <li><a href="dest.html">HTML link</a></li>
    <li><a href="no-extension">no ext link</a></li>
    <li><a href="http://www.example.com/index/sample.html">external link</a></li>
    <li><a href="mailto:example@example.com">e-mail link</a></li>
    <li><a media="">no href link</a></li>
<object data="download/toto.jpg" width="300" height="200"></object>
<script src="assets/js/bootstrap/bootsrap.css?v=20190101"></script>
</body>
</html>
"""


@pytest.fixture(scope="function")
def html_str_cn():
    """sample HTML content with chinese characters"""
    return """<html>
<body>
<ul>
    <li><a href="download/toto.pdf">PDF doc in 汉字</a></li>
    <li><a href="download/toto.txt">text file</a></li>
    <li><a href="dest.html">HTML link</a></li>
    <li><a href="no-extension">no ext link</a></li>
    <li><a href="http://www.example.com/index/sample.html">external link</a></li>
    <li><a href="mailto:example@example.com">e-mail link</a></li>
    <li><a media="">no href link</a></li>
<object data="download/toto.jpg" width="300" height="200"></object>
<script src="assets/js/bootstrap/bootsrap.css?v=20190101"></script>
</body>
</html>
"""


@pytest.fixture(scope="function")
def html_file(tmp_path: pathlib.Path, html_str: str) -> pathlib.Path:
    fpath = tmp_path / "test.html"
    with open(fpath, "w") as fh:
        fh.write(html_str)
    return fpath


@pytest.fixture(scope="function")
def build_data(tmp_path: pathlib.Path, png_image: pathlib.Path) -> dict[str, Any]:
    fpath = tmp_path / "test.zim"
    redirects_file = tmp_path / "redirects.tsv"
    with open(redirects_file, "w") as fh:
        fh.write(" \tAccueil\tBienvenue !!\twelcome\n")
        fh.write(" \tAccueil2\t\tcommons48.png\n")
        fh.write(" \timage\t\tcommons48.png\n")
    build_dir = tmp_path / "build"
    return {
        "build_dir": build_dir,
        "fpath": fpath,
        "name": "test-zim",
        "main_page": "welcome",
        "illustration": png_image.name,
        "title": "Test ZIM",
        "description": "A test ZIM",
        "date": None,
        "language": "fra",
        "creator": "test",
        "publisher": "test",
        "tags": ["test"],
        "redirects": [("picture", "commons48.png", "")],
        "redirects_file": redirects_file,
    }


@pytest.fixture(scope="function")
def counters():
    return {
        "text/html": 3,
        "application/warc-headers": 28364,
        "text/html;raw=true": 6336,
        "text/css": 47,
        "text/javascript": 98,
        "image/png": 968,
        "image/webp": 24,
        "application/json": 3694,
        "image/gif": 10274,
        "image/jpeg": 1582,
        "font/woff2": 25,
        "text/plain": 284,
        "application/atom+xml": 247,
        "application/x-www-form-urlencoded": 9,
        "video/mp4": 9,
        "application/x-javascript": 7,
        "application/xml": 1,
        "image/svg+xml": 5,
    }


class MetadataCase(NamedTuple):
    name: str
    value: Any
    valid: bool


@pytest.fixture(
    params=[
        MetadataCase("Name", 4, False),
        MetadataCase("Title", 4, False),
        MetadataCase("Creator", 4, False),
        MetadataCase("Publisher", 4, False),
        MetadataCase("Description", 4, False),
        MetadataCase("LongDescription", 4, False),
        MetadataCase("License", 4, False),
        MetadataCase("Relation", 4, False),
        MetadataCase("Relation", 4, False),
        MetadataCase("Flavour", 4, False),
        MetadataCase("Source", 4, False),
        MetadataCase("Scraper", 4, False),
        MetadataCase("Title", "में" * 30, True),
        MetadataCase("Title", "X" * 31, False),
        MetadataCase("Date", 4, False),
        MetadataCase("Date", datetime.datetime.now(), True),  # noqa: DTZ005
        MetadataCase(
            "Date", datetime.datetime(1969, 12, 31, 23, 59), True  # noqa: DTZ001
        ),
        MetadataCase("Date", datetime.date(1969, 12, 31), True),
        MetadataCase("Date", datetime.date.today(), True),  # noqa: DTZ011
        MetadataCase("Date", "1969-12-31", True),
        MetadataCase("Date", "1969-13-31", False),
        MetadataCase("Date", "2023/02/29", False),
        MetadataCase("Date", "2023-55-99", False),
        MetadataCase("Language", "xxx", False),
        MetadataCase("Language", "rmr", False),
        MetadataCase("Language", "eng", True),
        MetadataCase("Language", "fra", True),
        MetadataCase("Language", "bam", True),
        MetadataCase("Language", "fr", False),
        MetadataCase("Language", "en", False),
        MetadataCase("Language", "fra,eng", True),
        MetadataCase("Language", "fra,eng,bam", True),
        MetadataCase("Language", "fra,en,bam", False),
        MetadataCase("Language", "eng,", False),
        MetadataCase("Language", "eng, fra", False),
        MetadataCase("Counter", "1", False),
        MetadataCase("Description", "में" * 80, True),
        MetadataCase("Description", "X" * 81, False),
        MetadataCase("LongDescription", "में" * 4000, True),
        MetadataCase("LongDescription", "X" * 4001, False),
        MetadataCase(
            "LongDescription", None, True
        ),  # to be ignored in config_xxx methods
        MetadataCase("Tags", 4, False),
        MetadataCase("Tags", ["wikipedia", 4, "football"], False),
        MetadataCase("Tags", ("wikipedia", "football"), True),
        MetadataCase("Tags", ["wikipedia", "football"], True),
        MetadataCase("Tags", "wikipedia;football", True),
        # 1x1 PNG image
        MetadataCase(
            "Illustration_48x48@1",
            base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAAGXRFWHRTb2Z0d2FyZQBB"
                "ZG9iZSBJbWFnZVJlYWR5ccllPAAAAA9JREFUeNpi+P//P0CAAQAF/gL+Lc6J7gAAAABJ"
                "RU5ErkJggg=="
            ),
            False,
        ),
        MetadataCase(
            "Illustration_48x48@1",
            DEFAULT_DEV_ZIM_METADATA.Illustration_48x48_at_1,
            True,
        ),
        MetadataCase(
            "Illustration_48x48_at_1",
            DEFAULT_DEV_ZIM_METADATA.Illustration_48x48_at_1,
            True,
        ),
        MetadataCase(
            "Illustration_48x48_at_1",
            None,
            False,
        ),
        MetadataCase(
            "Illustration_96x96@1",
            DEFAULT_DEV_ZIM_METADATA.Illustration_48x48_at_1,
            False,
        ),
    ]
    + [MetadataCase(name, "", False) for name in MANDATORY_ZIM_METADATA_KEYS],
)
def metadata_case(request: pytest.FixtureRequest) -> MetadataCase:
    return request.param
