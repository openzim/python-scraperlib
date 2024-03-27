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
