""" Special item with customized index data and helper classes """

import io
import pathlib

import libzim.writer  # pyright: ignore[reportMissingModuleSource]

try:
    import pymupdf  # pyright: ignore[reportMissingTypeStubs]
except ImportError:  # pragma: no cover
    # pymupdf main module was named fitz before 1.24.3
    import fitz as pymupdf  # pyright: ignore[reportMissingTypeStubs]

from zimscraperlib import logger


class IndexData(libzim.writer.IndexData):
    """IndexData to properly pass indexing title and content to the libzim

    Both title and content have to be customized (title can be identical to item title
    or not).
    keywords is optional since it can be empty
    wordcount is optional ; if not passed, it is automaticaly computed from content
    """

    def __init__(
        self, title: str, content: str, keywords: str = "", wordcount: int | None = None
    ):
        # set wordcount first so that we know if we should override it based on content
        self.wordcount = wordcount
        self.title = title
        self.content = content
        self.keywords = keywords

    def has_indexdata(self) -> bool:
        return len(self.content) > 0 or len(self.title) > 0

    def get_title(self) -> str:
        return self.title

    def get_content(self) -> str:
        return self.content

    def get_keywords(self) -> str:
        return self.keywords

    def get_wordcount(self) -> int:
        return self.wordcount or 0

    @property
    def content(self):
        return self._content

    @content.setter
    def content(self, value: str):
        self._content = value
        if not self.wordcount:
            self.wordcount = len(self.content.split()) if self.content else 0


IGNORED_MUPDF_MESSAGES = [
    "lcms: not an ICC profile, invalid signature.",
    "format error: cmsOpenProfileFromMem failed",
    "ignoring broken ICC profile",
]


def get_pdf_index_data(
    *,
    content: str | bytes | None = None,
    fileobj: io.BytesIO | None = None,
    filepath: pathlib.Path | None = None,
) -> IndexData:
    """Returns the IndexData information for a given PDF

    PDF can be passed either as content or fileobject or filepath
    """

    # do not display all pymupdf errors, we will filter them afterwards
    pymupdf.TOOLS.mupdf_display_errors(  # pyright: ignore[reportUnknownMemberType]
        False
    )

    if content:
        doc = pymupdf.open(stream=content)
    elif fileobj:
        doc = pymupdf.open(stream=fileobj)
    else:
        doc = pymupdf.open(filename=filepath)
    metadata = (  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]
        doc.metadata
    )
    title = ""
    if metadata:  # pragma: no branch (always metadata in test PDFs)
        parts: list[str] = []
        for key in ["title", "author", "subject"]:
            if metadata.get(key):  # pyright: ignore[reportUnknownMemberType]
                parts.append(
                    metadata[key]  # pyright: ignore[reportUnknownArgumentType]
                )
        if parts:  # pragma: no branch (always metadata in test PDFs)
            title = " - ".join(parts)

    content = "\n".join(
        page.get_text()  # pyright: ignore[reportUnknownArgumentType, reportUnknownMemberType, reportAttributeAccessIssue]
        for page in doc
    )

    # build list of messages and filter messages which are known to not be relevant
    # in our use-case
    mupdf_messages = "\n".join(
        warning
        for warning in pymupdf.TOOLS.mupdf_warnings().splitlines()
        if warning not in IGNORED_MUPDF_MESSAGES
    )

    if mupdf_messages:
        logger.warning(
            f"PyMuPDF issues:\n{mupdf_messages}"
        )  # pragma: no cover (no known error in test PDFs)

    return IndexData(
        title=title,
        content=content,
    )
