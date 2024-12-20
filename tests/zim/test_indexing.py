import io
import pathlib

import libzim.writer  # pyright: ignore[reportMissingModuleSource]
import pytest

from zimscraperlib.zim import Archive, Creator
from zimscraperlib.zim.indexing import IndexData, get_pdf_index_data
from zimscraperlib.zim.items import StaticItem


def test_indexing_html_with_libzim(tmp_path: pathlib.Path, html_file: pathlib.Path):
    """Two HTML entries automatically indexed by libzim"""
    fpath = tmp_path / "test.zim"
    main_path = "welcome"
    with Creator(fpath, main_path).config_dev_metadata() as creator:
        creator.add_item_for(
            fpath=html_file,
            path="welcome",
            mimetype="text/html",
        )
        creator.add_item_for(
            content="foo",
            path="welcome2",
            mimetype="text/html",
        )
    assert fpath.exists()

    reader = Archive(fpath)
    assert reader.get_search_results_count("link") == 1
    assert reader.get_search_results_count("foo") == 1


def test_indexing_disabled(tmp_path: pathlib.Path, html_file: pathlib.Path):
    """One HTML entry is disabled from libzim indexing"""
    fpath = tmp_path / "test.zim"
    main_path = "welcome"
    with Creator(fpath, main_path).config_dev_metadata() as creator:
        creator.add_item_for(
            fpath=html_file,
            path="welcome",
            mimetype="text/html",
            auto_index=False,
        )
        creator.add_item(
            StaticItem(
                content="foo",
                path="welcome2",
                mimetype="text/html",
            )
        )
    assert fpath.exists()

    reader = Archive(fpath)
    assert reader.get_search_results_count("link") == 0
    assert reader.get_search_results_count("foo") == 1


def test_indexing_custom(tmp_path: pathlib.Path, html_file: pathlib.Path):
    """One HTML entry has custom indexing data"""
    fpath = tmp_path / "test.zim"
    main_path = "welcome"
    with Creator(fpath, main_path).config_dev_metadata() as creator:
        creator.add_item_for(
            fpath=html_file,
            path="welcome",
            mimetype="text/html",
            index_data=IndexData(title="blu", content="bar"),
        )
        creator.add_item(
            StaticItem(
                content="foo",
                path="welcome2",
                mimetype="text/html",
            )
        )
    assert fpath.exists()

    reader = Archive(fpath)
    assert reader.get_search_results_count("bar") == 1
    assert reader.get_search_results_count("foo") == 1
    assert "welcome" in list(reader.get_suggestions("blu"))


def test_indexing_item_is_front(tmp_path: pathlib.Path, png_image: pathlib.Path):
    """Create a ZIM with a single item with customized title and content for indexing"""
    fpath = tmp_path / "test.zim"
    main_path = "welcome"
    with Creator(fpath, main_path).config_dev_metadata() as creator:
        creator.add_item(
            StaticItem(
                filepath=png_image,
                path="welcome",
                title="brain food",  # title used for suggestions
                index_data=IndexData(
                    title="screen", content="car"  # title and content used for search
                ),
                hints={libzim.writer.Hint.FRONT_ARTICLE: True},
            )
        )
    assert fpath.exists()

    reader = Archive(fpath)
    assert "welcome" in list(reader.get_suggestions("brain"))
    assert "welcome" in list(reader.get_suggestions("food"))
    assert "welcome" not in list(reader.get_suggestions("screen"))
    assert "welcome" not in list(reader.get_suggestions("car"))
    assert reader.get_search_results_count("screen") == 1
    assert reader.get_search_results_count("car") == 1
    assert reader.get_search_results_count("brain") == 0
    assert reader.get_search_results_count("food") == 0


def test_indexing_item_not_front(tmp_path: pathlib.Path, png_image: pathlib.Path):
    fpath = tmp_path / "test.zim"
    main_path = "welcome"
    with Creator(fpath, main_path).config_dev_metadata() as creator:
        creator.add_item(
            StaticItem(
                filepath=png_image,
                path="welcome",
                title="brain food",  # title used for suggestions
                index_data=IndexData(
                    title="screen", content="car"  # title and content used for search
                ),
                hints={libzim.writer.Hint.FRONT_ARTICLE: False},  # mark as not front
            )
        )
    assert fpath.exists()

    reader = Archive(fpath)
    # "brain" works as a suggestion but "food" doesn't work because since no front
    # article is present in the zim file, libzim doesn't create a title xapian index.
    # so, when searching suggestion, libzim is fallback to a binary search on the title
    # and return only article starting by the query.
    # see https://github.com/openzim/libzim/issues/902#issuecomment-2223050129
    assert "welcome" in list(reader.get_suggestions("brain"))
    assert "welcome" not in list(reader.get_suggestions("food"))
    assert "welcome" not in list(reader.get_suggestions("screen"))
    assert "welcome" not in list(reader.get_suggestions("car"))
    assert reader.get_search_results_count("screen") >= 1
    assert reader.get_search_results_count("car") >= 1
    assert reader.get_search_results_count("brain") == 0
    assert reader.get_search_results_count("food") == 0


def _assert_pdf_zim(fpath: pathlib.Path):
    assert fpath.exists()

    reader = Archive(fpath)
    assert "welcome" in list(reader.get_suggestions("microsoft"))
    assert "welcome" in list(reader.get_suggestions("c8clark"))
    assert "welcome" not in list(reader.get_suggestions("appropriate"))
    assert "welcome" not in list(reader.get_suggestions("the"))
    assert "welcome" not in list(reader.get_suggestions("brain"))
    assert "welcome" not in list(reader.get_suggestions("food"))
    assert reader.get_search_results_count("appropriate") == 1
    assert reader.get_search_results_count("the") == 1
    assert (
        reader.get_search_results_count("microsoft") == 1  # title is used as index data
    )
    assert (
        reader.get_search_results_count("c8clark") == 1  # title is used as index data
    )


def _assert_png_zim(fpath: pathlib.Path):
    assert fpath.exists()

    reader = Archive(fpath)
    assert "welcome" in list(reader.get_suggestions("brain"))
    assert "welcome" in list(reader.get_suggestions("food"))
    assert "welcome" not in list(reader.get_suggestions("bar"))
    assert "welcome" not in list(reader.get_suggestions("feed"))


def test_indexing_item_pdf_filepath(
    tmp_path: pathlib.Path, encrypted_pdf_file: pathlib.Path
):
    """A PDF item can be automatically indexed"""
    fpath = tmp_path / "test.zim"
    main_path = "welcome"
    with Creator(fpath, main_path).config_dev_metadata() as creator:
        creator.add_item(
            StaticItem(
                filepath=encrypted_pdf_file,
                path="welcome",
                hints={libzim.writer.Hint.FRONT_ARTICLE: True},
            )
        )
    _assert_pdf_zim(fpath)


def test_indexing_item_pdf_fileobj(
    tmp_path: pathlib.Path, encrypted_pdf_file: pathlib.Path
):
    """A PDF item can be automatically indexed"""
    fpath = tmp_path / "test.zim"
    main_path = "welcome"
    with Creator(fpath, main_path).config_dev_metadata() as creator:
        fileobj = io.BytesIO()
        fileobj.write(encrypted_pdf_file.read_bytes())
        creator.add_item(
            StaticItem(
                fileobj=fileobj,
                path="welcome",
                hints={libzim.writer.Hint.FRONT_ARTICLE: True},
            )
        )
    _assert_pdf_zim(fpath)


def test_indexing_item_pdf_content(
    tmp_path: pathlib.Path, encrypted_pdf_file: pathlib.Path
):
    """A PDF item can be automatically indexed"""
    fpath = tmp_path / "test.zim"
    main_path = "welcome"
    with Creator(fpath, main_path).config_dev_metadata() as creator:
        creator.add_item(
            StaticItem(
                content=encrypted_pdf_file.read_bytes(),
                path="welcome",
                title=None,  # title not set will be set to PDF title
                hints={libzim.writer.Hint.FRONT_ARTICLE: True},
            )
        )
    _assert_pdf_zim(fpath)


def test_indexing_item_png_filepath(tmp_path: pathlib.Path, png_image: pathlib.Path):
    """A PNG item cannot automatically be indexed but it works properly"""
    fpath = tmp_path / "test.zim"
    main_path = "welcome"
    with Creator(fpath, main_path).config_dev_metadata() as creator:
        creator.add_item(
            StaticItem(
                filepath=png_image,
                path="welcome",
                title="brain food",
                hints={libzim.writer.Hint.FRONT_ARTICLE: True},
            )
        )


def test_indexing_item_png_fileobj(tmp_path: pathlib.Path, png_image: pathlib.Path):
    """A PNG item cannot automatically be indexed but it works properly"""
    fpath = tmp_path / "test.zim"
    main_path = "welcome"
    with Creator(fpath, main_path).config_dev_metadata() as creator:
        fileobj = io.BytesIO()
        fileobj.write(png_image.read_bytes())
        creator.add_item(
            StaticItem(
                fileobj=fileobj,
                path="welcome",
                title="brain food",
                hints={libzim.writer.Hint.FRONT_ARTICLE: True},
            )
        )
    _assert_png_zim(fpath)


def test_indexing_item_png_content(tmp_path: pathlib.Path, png_image: pathlib.Path):
    """A PNG item cannot automatically be indexed but it works properly"""
    fpath = tmp_path / "test.zim"
    main_path = "welcome"
    with Creator(fpath, main_path).config_dev_metadata() as creator:
        creator.add_item(
            StaticItem(
                content=png_image.read_bytes(),
                path="welcome",
                title="brain food",
                hints={libzim.writer.Hint.FRONT_ARTICLE: True},
            )
        )
    _assert_png_zim(fpath)


@pytest.mark.parametrize(
    "pdf_no, expected_title, expected_word_count",
    [
        (1, "Microsoft Word - Placeholder Documentation.docx - c8clark", 11),
        (
            2,
            "Military Dermatology (Redacted) - Office of the Surgeon General - 1994",
            304419,
        ),
    ],
)
def test_get_pdf_index_data(
    pdf_no: int,
    expected_title: str,
    expected_word_count: int,
    encrypted_pdf_file: pathlib.Path,
    encrypted_pdf_content: pathlib.Path,
    big_pdf_file: pathlib.Path,
    big_pdf_content: pathlib.Path,
):

    index_data = get_pdf_index_data(
        filepath=encrypted_pdf_file if pdf_no == 1 else big_pdf_file
    )
    assert index_data.get_title() == expected_title
    # actual index content is dependent on the MuPDF version used by PyMuPDF
    # this checks that index is large-enough
    content_size = len(
        (encrypted_pdf_content if pdf_no == 1 else big_pdf_content).read_text()
    )
    assert len(index_data.get_content()) >= content_size * 0.9
    assert index_data.has_indexdata()
    assert index_data.get_wordcount() == expected_word_count
    assert index_data.get_keywords() == ""


def test_indexing_item_pdf_custom_title(
    tmp_path: pathlib.Path, encrypted_pdf_file: pathlib.Path
):
    """Test case with a custom title is passed, it is not overwritten by PDF title"""
    fpath = tmp_path / "test.zim"
    main_path = "welcome"
    with Creator(fpath, main_path).config_dev_metadata() as creator:
        creator.add_item(
            StaticItem(
                filepath=encrypted_pdf_file,
                path="welcome",
                title="brain food",
                hints={libzim.writer.Hint.FRONT_ARTICLE: True},
            )
        )

    assert fpath.exists()

    reader = Archive(fpath)
    assert "welcome" not in list(reader.get_suggestions("microsoft"))
    assert "welcome" not in list(reader.get_suggestions("c8clark"))
    assert "welcome" not in list(reader.get_suggestions("appropriate"))
    assert "welcome" not in list(reader.get_suggestions("the"))
    assert "welcome" in list(reader.get_suggestions("brain"))
    assert "welcome" in list(reader.get_suggestions("food"))
    assert reader.get_search_results_count("appropriate") == 1
    assert reader.get_search_results_count("the") == 1
    assert reader.get_search_results_count("microsoft") == 1
    assert reader.get_search_results_count("c8clark") == 1


@pytest.mark.parametrize(
    "content, wordcount, expected_wordcount",
    [
        ("foo", None, 1),
        ("foo bar", None, 2),
        ("  foo    bar  ", None, 2),
        (
            "foo bar",
            123,
            123,
        ),  # wordcount is passed so it is not automatically computed
    ],
)
def test_index_data_wordcount(
    content: str, wordcount: int | None, expected_wordcount: int
):
    assert (
        IndexData(title="foo", content=content, wordcount=wordcount).get_wordcount()
        == expected_wordcount
    )
