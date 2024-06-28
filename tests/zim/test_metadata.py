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
        ("Language", "fra;eng"),
        ("Language", "fra, eng"),
    ],
)
def test_validate_language_invalid(name: str, value: Iterable[str] | str):
    with pytest.raises(ValueError, match=re.escape("is not ISO-639-3")):
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
def test_validate_tags(tags, is_valid):
    if is_valid:
        metadata.validate_tags("Tags", tags)
    else:
        with pytest.raises(ValueError):
            metadata.validate_tags("Tags", tags)
