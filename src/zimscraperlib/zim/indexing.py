"""Special item with customized index data and helper classes"""

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
    # MuPDF only knows EPUB 2 but reads EPUB 3 documents fine
    "unknown epub version: 3.0",
]

# messages carrying a document-specific detail, ignored by prefix; images and
# styles do not matter for the text content
IGNORED_MUPDF_MESSAGE_PREFIXES = (
    "html: cannot load image",
    "syntax error: css syntax error",
)


def get_pdf_index_data(
    *,
    content: str | bytes | None = None,
    fileobj: io.BytesIO | None = None,
    filepath: pathlib.Path | None = None,
) -> IndexData:
    """Returns the IndexData information for a given PDF

    PDF can be passed either as content or fileobject or filepath
    """
    return _get_document_index_data(
        filetype="pdf", content=content, fileobj=fileobj, filepath=filepath
    )


def get_epub_index_data(
    *,
    content: str | bytes | None = None,
    fileobj: io.BytesIO | None = None,
    filepath: pathlib.Path | None = None,
) -> IndexData:
    """Returns the IndexData information for a given EPUB

    EPUB can be passed either as content or fileobject or filepath
    """
    return _get_document_index_data(
        filetype="epub", content=content, fileobj=fileobj, filepath=filepath
    )


def _get_document_index_data(
    *,
    filetype: str,
    content: str | bytes | None = None,
    fileobj: io.BytesIO | None = None,
    filepath: pathlib.Path | None = None,
) -> IndexData:
    """IndexData of any document PyMuPDF can read, title built from its metadata"""

    # do not display all pymupdf errors, we will filter them afterwards
    pymupdf.TOOLS.mupdf_display_errors(  # pyright: ignore[reportUnknownMemberType]
        False
    )

    if content:
        doc = pymupdf.open(stream=content, filetype=filetype)
    elif fileobj:
        doc = pymupdf.open(stream=fileobj, filetype=filetype)
    else:
        doc = pymupdf.open(filename=filepath, filetype=filetype)
    metadata = (  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]
        doc.metadata
    )
    title = ""
    if metadata:  # pragma: no branch (always metadata in test documents)
        parts: list[str] = []
        for key in ["title", "author", "subject"]:
            if metadata.get(key):  # pyright: ignore[reportUnknownMemberType]
                parts.append(
                    metadata[key]  # pyright: ignore[reportUnknownArgumentType]
                )
        if parts:  # pragma: no branch (always metadata in test documents)
            title = " - ".join(parts)

    def get_page_content(page: pymupdf.Page) -> str:
        text = (  # pyright: ignore[reportUnknownVariableType]
            page.get_text()  # pyright: ignore[reportUnknownMemberType]
        )
        if not isinstance(text, str):  # pragma: no cover
            raise Exception("Unexpected text content")
        return text

    content = "\n".join(get_page_content(page) for page in doc)

    # build list of messages and filter messages which are known to not be relevant
    # in our use-case
    mupdf_messages = "\n".join(
        warning
        for warning in pymupdf.TOOLS.mupdf_warnings().splitlines()
        if warning not in IGNORED_MUPDF_MESSAGES
        and not warning.startswith(IGNORED_MUPDF_MESSAGE_PREFIXES)
    )

    if mupdf_messages:
        logger.warning(
            f"PyMuPDF issues:\n{mupdf_messages}"
        )  # pragma: no cover (no known error in test documents)

    return IndexData(
        title=title,
        content=content,
    )
