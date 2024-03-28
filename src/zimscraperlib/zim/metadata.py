from __future__ import annotations

import datetime
import re
from collections.abc import Iterable
from typing import Any

from zimscraperlib.constants import (
    ILLUSTRATIONS_METADATA_RE,
    MANDATORY_ZIM_METADATA_KEYS,
    MAXIMUM_DESCRIPTION_METADATA_LENGTH,
    MAXIMUM_LONG_DESCRIPTION_METADATA_LENGTH,
    RECOMMENDED_MAX_TITLE_LENGTH,
)
from zimscraperlib.i18n import is_valid_iso_639_3
from zimscraperlib.image.probing import is_valid_image


def validate_required_values(name: str, value: Any):
    """ensures required ones have a value (spec doesnt requires it but makes sense)"""
    if name in MANDATORY_ZIM_METADATA_KEYS and not value:
        raise ValueError(f"Missing value for {name}")


def validate_standard_str_types(name: str, value: str):
    """ensures standard string metadata are indeed str"""
    if name in (
        "Name",
        "Title",
        "Creator",
        "Publisher",
        "Description",
        "LongDescription",
        "License",
        "Relation",
        "Relation",
        "Flavour",
        "Source",
        "Scraper",
    ) and not isinstance(value, str):
        raise ValueError(f"Invalid type for {name}")


def validate_title(name: str, value: str):
    """ensures Title metadata is within recommended length"""
    if name == "Title" and len(value) > RECOMMENDED_MAX_TITLE_LENGTH:
        raise ValueError(f"{name} is too long.")


def validate_date(name: str, value: datetime.datetime | datetime.date | str):
    """ensures Date metadata can be casted to an ISO 8601 string"""
    if name == "Date":
        if not isinstance(value, (datetime.datetime, datetime.date, str)):
            raise ValueError(f"Invalid type for {name}.")
        elif isinstance(value, str):
            match = re.match(r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})", value)
            try:
                datetime.date(
                    **{
                        k: int(v)
                        for k, v in match.groupdict().items()  # pyright: ignore
                    }
                )
            except Exception as exc:
                raise ValueError(f"Invalid {name} format: {exc}") from None


def validate_language(name: str, value: Iterable[str] | str):
    """ensures Language metadata is a single or list of ISO-639-3 codes"""
    if name == "Language":
        if isinstance(value, str):
            value = value.split(",")
        for code in value:
            if not is_valid_iso_639_3(code):
                raise ValueError(f"{code} is not ISO-639-3.")


def validate_counter(name: str, value: str):  # noqa: ARG001
    """ensures Counter metadata is not manually set"""
    if name == "Counter":
        raise ValueError(f"{name} cannot be set. libzim sets it.")


def validate_description(name: str, value: str):
    """ensures Description metadata is with required length"""
    if name == "Description" and len(value) > MAXIMUM_DESCRIPTION_METADATA_LENGTH:
        raise ValueError(f"{name} is too long.")


def validate_longdescription(name: str, value: str):
    """ensures LongDescription metadata is with required length"""
    if (
        name == "LongDescription"
        and len(value) > MAXIMUM_LONG_DESCRIPTION_METADATA_LENGTH
    ):
        raise ValueError(f"{name} is too long.")


def validate_tags(name: str, value: Iterable[str] | str):
    """ensures Tags metadata is either one or a list of strings"""
    if name == "Tags" and (
        not isinstance(value, Iterable)
        or not all(isinstance(tag, str) for tag in value)
    ):
        raise ValueError(f"Invalid type(s) for {name}")


def validate_illustrations(name: str, value: bytes):
    """ensures illustrations are PNG images or the advertised size"""
    if name.startswith("Illustration_"):
        match = ILLUSTRATIONS_METADATA_RE.match(name)
        if match and not is_valid_image(
            image=value,
            imformat="PNG",
            size=(
                int(match.groupdict()["width"]),
                int(match.groupdict()["height"]),
            ),
        ):
            raise ValueError(
                f"{name} is not a "
                f"{match.groupdict()['width']}x{match.groupdict()['height']} "
                "PNG Image"
            )
