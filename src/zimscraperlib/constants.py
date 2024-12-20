import pathlib
import re

from zimscraperlib.__about__ import __version__

ROOT_DIR = pathlib.Path(__file__).parent
NAME = pathlib.Path(__file__).parent.name
SCRAPER = f"{NAME} {__version__}"
VERSION = __version__
CONTACT = "dev@openzim.org"
DEFAULT_USER_AGENT = f"{NAME}/{__version__} ({CONTACT})"

UTF8 = "UTF-8"

# list of Image formats witout Alpha Channel support
ALPHA_NOT_SUPPORTED = ["JPEG", "BMP", "EPS", "PCX"]

# list of mimetypes we consider articles using it should default to FRONT_ARTICLE
FRONT_ARTICLE_MIMETYPES = ["text/html"]

RECOMMENDED_MAX_TITLE_LENGTH = 30
MAXIMUM_DESCRIPTION_METADATA_LENGTH = 80
MAXIMUM_LONG_DESCRIPTION_METADATA_LENGTH = 4000

ILLUSTRATIONS_METADATA_RE = re.compile(
    r"^Illustration_(?P<height>\d+)x(?P<width>\d+)@(?P<scale>\d+)$"
)

# default timeout to get responses from upstream when doing web requests ; this is not
# the total time it gets to download the whole resource
DEFAULT_WEB_REQUESTS_TIMEOUT = 10
