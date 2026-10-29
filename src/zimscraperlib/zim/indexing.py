"""Special item with customized index data and helper classes"""

import io
import pathlib

import libzim.writer  # pyright: ignore[reportMissingModuleSource]
import pymupdf  # pyright: ignore[reportMissingTypeStubs]

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


def get_pdf_title(
    *,
    content: str | bytes | None = None,
    fileobj: io.BytesIO | None = None,
    filepath: pathlib.Path | None = None,
) -> str:
    """Returns the title of a given PDF, built from its own metadata

    Cheaper than get_pdf_index_data when only the title is needed, since it does
    not extract the document's full text content.

    PDF can be passed either as content or fileobject or filepath
    """
    return _get_document_title(
        filetype="pdf", content=content, fileobj=fileobj, filepath=filepath
    )


def get_epub_title(
    *,
    content: str | bytes | None = None,
    fileobj: io.BytesIO | None = None,
    filepath: pathlib.Path | None = None,
) -> str:
    """Returns the title of a given EPUB, built from its own metadata

    Cheaper than get_epub_index_data when only the title is needed, since it does
    not extract the document's full text content.

    EPUB can be passed either as content or fileobject or filepath
    """
    return _get_document_title(
        filetype="epub", content=content, fileobj=fileobj, filepath=filepath
    )


def _open_document(
    filetype: str,
    *,
    content: str | bytes | None = None,
    fileobj: io.BytesIO | None = None,
    filepath: pathlib.Path | None = None,
) -> pymupdf.Document:
    """Open a document with PyMuPDF, passed either as content, fileobject or
    filepath"""

    # do not display all pymupdf errors, we will filter them afterwards
    pymupdf.TOOLS.mupdf_display_errors(  # pyright: ignore[reportUnknownMemberType]
        False
    )

    if content:
        return pymupdf.open(stream=content, filetype=filetype)
    elif fileobj:
        return pymupdf.open(stream=fileobj, filetype=filetype)
    else:
        return pymupdf.open(filename=filepath, filetype=filetype)


def _get_metadata_title(doc: pymupdf.Document) -> str:
    """Build a title from a document's own metadata (title/author/subject)"""
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
    return title


def _log_mupdf_warnings():
    """Log PyMuPDF warnings accumulated since errors were last silenced/fetched,
    filtering out messages which are known to not be relevant in our use-case"""
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


def _get_document_title(
    *,
    filetype: str,
    content: str | bytes | None = None,
    fileobj: io.BytesIO | None = None,
    filepath: pathlib.Path | None = None,
) -> str:
    """Title of any document PyMuPDF can read, built from its own metadata"""
    doc = _open_document(filetype, content=content, fileobj=fileobj, filepath=filepath)
    title = _get_metadata_title(doc)
    _log_mupdf_warnings()
    return title


def _get_document_index_data(
    *,
    filetype: str,
    content: str | bytes | None = None,
    fileobj: io.BytesIO | None = None,
    filepath: pathlib.Path | None = None,
) -> IndexData:
    """IndexData of any document PyMuPDF can read, title built from its metadata"""

    doc = _open_document(filetype, content=content, fileobj=fileobj, filepath=filepath)
    title = _get_metadata_title(doc)

    def get_page_content(page: pymupdf.Page) -> str:
        text = (  # pyright: ignore[reportUnknownVariableType]
            page.get_text()  # pyright: ignore[reportUnknownMemberType]
        )
        if not isinstance(text, str):  # pragma: no cover
            raise Exception("Unexpected text content")
        return text

    content = "\n".join(get_page_content(page) for page in doc)

    _log_mupdf_warnings()

    return IndexData(
        title=title,
        content=content,
    )
