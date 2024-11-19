from __future__ import annotations

import re
from collections.abc import Iterable

import pytest

from zimscraperlib.zim import metadata


@pytest.mark.parametrize(
    "name, value",
    [
        ("Language", "fra"),
        ("Language", "fra,eng"),
        ("Language", ["fra", "eng"]),
        ("Other", "not_an_iso_639_3_code"),
    ],
)
def test_validate_language_valid(name: str, value: Iterable[str] | str):
    metadata.validate_language(name, value)


@pytest.mark.parametrize(
    "name, value",
    [
        ("Language", "fr"),
        ("Language", "fra;eng"),  # bad separator
        ("Language", "fra, eng"),  # bad space
        ("Language", ["fr", "eng"]),
    ],
)
def test_validate_language_invalid(name: str, value: Iterable[str] | str):
    with pytest.raises(ValueError, match=re.escape("is not ISO-639-3")):
        metadata.validate_language(name, value)


@pytest.mark.parametrize(
    "name, value",
    [
        ("Language", "fra,fra"),
        ("Language", ["fra", "fra"]),
    ],
)
def test_validate_language_duplicate(name: str, value: Iterable[str] | str):
    with pytest.raises(ValueError, match=re.escape("Duplicate langs are not valid")):
        metadata.validate_language(name, value)


@pytest.mark.parametrize(
    "name, value",
    [
        ("Language", 123),
        ("Language", b"fra"),
        ("Language", ["fra", 123]),
    ],
)
def test_validate_language_bad_type(name: str, value: str):
    with pytest.raises(ValueError, match=re.escape("Invalid type for Language: ")):
        metadata.validate_language(name, value)


@pytest.mark.parametrize(
    "tags, is_valid",
    [
        pytest.param("", True, id="empty_string"),
        pytest.param("tag1", True, id="empty_string"),
        pytest.param("taaaag1", True, id="many_letters"),
        pytest.param("tag1;tag2", True, id="semi_colon_distinct_1"),
        pytest.param("tag2;tag2", False, id="semi_colon_identical"),
        pytest.param("tag,1;tug,1", True, id="semi_colon_distinct_2"),
        pytest.param(
            "tag1,tag2", True, id="comma"
        ),  # we cannot say that this ought to be a tags separator
        pytest.param({"tag1"}, True, id="one_tag_in_set"),
        pytest.param({"tag1", "tag2"}, True, id="two_tags_in_set"),
        pytest.param(1, False, id="one_int"),
        pytest.param(None, False, id="none_value"),
        pytest.param(["tag1", "tag2"], True, id="two_distinct"),
        pytest.param(["tag1", "tag1"], False, id="two_identical"),
        pytest.param(["tag1", 1], False, id="int_in_list"),
    ],
)
def test_validate_tags(
    tags: Iterable[str] | str,
    is_valid: bool,  # noqa: FBT001 # used only in tests
):
    if is_valid:
        metadata.validate_tags("Tags", tags)
    else:
        with pytest.raises(ValueError):
            metadata.validate_tags("Tags", tags)


@pytest.mark.parametrize(
    "name, value",
    [
        ("Title", 123),
        ("Title", b"title"),
        ("Title", ["a", "title"]),
    ],
)
def test_validate_title_bad_type(name: str, value: str):
    with pytest.raises(ValueError, match=re.escape("Title is not a str.")):
        metadata.validate_title(name, value)


@pytest.mark.parametrize(
    "name, value",
    [
        ("Date", 123),
        ("Date", b"12/12/2024"),
        ("Date", ["12", "12", "2024"]),
    ],
)
def test_validate_date_bad_type(name: str, value: str):
    with pytest.raises(ValueError, match=re.escape("Invalid type for Date: ")):
        metadata.validate_date(name, value)


@pytest.mark.parametrize(
    "name, value",
    [
        ("Description", 123),
        ("Description", b"description"),
        ("Description", ["a", "description"]),
    ],
)
def test_validate_description_bad_type(name: str, value: str):
    with pytest.raises(ValueError, match=re.escape("Invalid type for Description: ")):
        metadata.validate_description(name, value)


@pytest.mark.parametrize(
    "name, value",
    [
        ("LongDescription", 123),
        ("LongDescription", b"description"),
        ("LongDescription", ["a", "description"]),
    ],
)
def test_validate_long_description_bad_type(name: str, value: str):
    with pytest.raises(
        ValueError, match=re.escape("Invalid type for LongDescription: ")
    ):
        metadata.validate_longdescription(name, value)


@pytest.mark.parametrize(
    "name, value",
    [
        ("Illustration_48x48@1", 123),
        ("Illustration_48x48@1", "illustration"),
        ("Illustration_48x48@1", [b"an", b"illustration"]),
    ],
)
def test_validate_illustration_bad_type(name: str, value: str):
    with pytest.raises(
        ValueError, match=re.escape("Invalid type for Illustration_48x48@1: ")
    ):
        metadata.validate_illustrations(name, value)


@pytest.mark.parametrize(
    "name",
    [
        "Name",
        "Title",
        "Creator",
        "Publisher",
        "Date",
        "Description",
        "Language",
        "Illustration_48x48@1",
        "LongDescription",
        "Counter",
        "Tags",
        "Name",
        "Title",
        "Creator",
        "Publisher",
        "Description",
        "LongDescription",
        "License",
        "Relation",
        "Flavour",
        "Source",
        "Scraper",
    ],
)
def test_validate_ignores(name: str):
    if name != "Title":
        metadata.validate_title(name, "Foo")
    if name != "Date":
        metadata.validate_date(name, "Foo")
    if name != "Description":
        metadata.validate_description(name, "Foo")
    if name != "LongDescription":
        metadata.validate_longdescription(name, "Foo")
    if name != "Language":
        metadata.validate_language(name, "Foo")
    if not name.startswith("Illustration"):
        metadata.validate_illustrations(name, "Foo")
    if name != "Counter":
        metadata.validate_counter(name, "Foo")
    if name != "Tags":
        metadata.validate_tags(name, "Foo")
    if name not in metadata.MANDATORY_ZIM_METADATA_KEYS:
        metadata.validate_required_values(name, None)
    if name not in (
        "Name",
        "Title",
        "Creator",
        "Publisher",
        "Description",
        "LongDescription",
        "License",
        "Relation",
        "Flavour",
        "Source",
        "Scraper",
    ):
        metadata.validate_standard_str_types(name, 123)
