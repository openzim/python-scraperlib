from __future__ import annotations

import base64
import datetime
import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, NamedTuple

import regex

from zimscraperlib.i18n import is_valid_iso_639_3
from zimscraperlib.image.probing import is_valid_image

RECOMMENDED_MAX_TITLE_LENGTH = 30
MAXIMUM_DESCRIPTION_METADATA_LENGTH = 80
MAXIMUM_LONG_DESCRIPTION_METADATA_LENGTH = 4000

ILLUSTRATIONS_METADATA_RE = re.compile(
    r"^Illustration_(?P<height>\d+)x(?P<width>\d+)@(?P<scale>\d+)$"
)

RawMetadataValue = (
    None | float | int | bytes | str | datetime.datetime | datetime.date | Iterable[str]
)

CleanMetadataValue = bytes | str

# All control characters are disallowed in str metadata except \n, \r and \t
UNWANTED_CONTROL_CHARACTERS_REGEX = regex.compile(r"(?![\n\t\r])\p{C}")


@dataclass
class StandardMetadata:
    Name: str
    Language: str
    Title: str
    Creator: str
    Publisher: str
    Date: datetime.datetime | datetime.date | str
    Illustration_48x48_at_1: bytes
    Description: str
    LongDescription: str | None = None
    Tags: Iterable[str] | str | None = None
    Scraper: str | None = None
    Flavour: str | None = None
    Source: str | None = None
    License: str | None = None
    Relation: str | None = None

    def copy(self) -> StandardMetadata:
        return StandardMetadata(
            Name=self.Name,
            Language=self.Language,
            Title=self.Title,
            Creator=self.Creator,
            Publisher=self.Publisher,
            Date=self.Date,
            Illustration_48x48_at_1=self.Illustration_48x48_at_1,
            Description=self.Description,
            LongDescription=self.LongDescription,
            Tags=self.Tags,
            Scraper=self.Scraper,
            Flavour=self.Flavour,
            Source=self.Source,
            License=self.License,
            Relation=self.Relation,
        )


# list of mandatory meta tags of the zim file.
MANDATORY_ZIM_METADATA_KEYS = [
    "Name",
    "Title",
    "Creator",
    "Publisher",
    "Date",
    "Description",
    "Language",
    "Illustration_48x48@1",
]

DEFAULT_DEV_ZIM_METADATA = StandardMetadata(
    Name="Test Name",
    Title="Test Title",
    Creator="Test Creator",
    Publisher="Test Publisher",
    Date="2023-01-01",
    Description="Test Description",
    Language="fra",
    # blank 48x48 transparent PNG
    Illustration_48x48_at_1=base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAADAAAAAwAQMAAABtzGvEAAAAGXRFWHRTb2Z0d2FyZQBB"
        "ZG9iZSBJbWFnZVJlYWR5ccllPAAAAANQTFRFR3BMgvrS0gAAAAF0Uk5TAEDm2GYAAAAN"
        "SURBVBjTY2AYBdQEAAFQAAGn4toWAAAAAElFTkSuQmCC"
    ),
)


class Metadata(NamedTuple):
    key: str
    value: RawMetadataValue


def convert_and_check_metadata(
    name: str,
    value: RawMetadataValue,
) -> CleanMetadataValue:
    """Convert metadata to appropriate type for few known usecase and check type

    Date: converts date and datetime to string YYYY-MM-DD
    Tags: converts iterable to string with semi-colon separator

    Also checks removes unwanted control characters in string, and checks that final
    type is appropriate for libzim (str or bytes)
    """
    if name == "Date" and isinstance(value, datetime.date | datetime.datetime):
        value = value.strftime("%Y-%m-%d")
    if (
        name == "Tags"
        and not isinstance(value, str)
        and not isinstance(value, bytes)
        and isinstance(value, Iterable)
    ):
        if not all(isinstance(tag, str) for tag in value):
            raise ValueError("All tag values must be str")
        value = ";".join(value)

    if isinstance(value, str):
        value = UNWANTED_CONTROL_CHARACTERS_REGEX.sub("", value).strip(" \r\n\t")

    if not isinstance(value, str) and not isinstance(value, bytes):
        raise ValueError(f"Invalid type for {name}: {type(value)}")

    return value


def nb_grapheme_for(value: str) -> int:
    """Number of graphemes (visually perceived characters) in a given string"""
    return len(regex.findall(r"\X", value))


def validate_required_values(name: str, value: Any):
    """ensures required ones have a value (spec doesnt requires it but makes sense)"""
    if name in MANDATORY_ZIM_METADATA_KEYS and not value:
        raise ValueError(f"Missing value for {name}")


def validate_standard_str_types(
    name: str,
    value: CleanMetadataValue,
):
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
        "Flavour",
        "Source",
        "Scraper",
    ) and not isinstance(value, str):
        raise ValueError(f"Invalid type for {name}: {type(value)}")


def validate_title(name: str, value: str):
    """ensures Title metadata is within recommended length"""
    if name == "Title" and nb_grapheme_for(value) > RECOMMENDED_MAX_TITLE_LENGTH:
        raise ValueError(f"{name} is too long.")


def validate_date(name: str, value: datetime.datetime | datetime.date | str):
    """ensures Date metadata can be casted to an ISO 8601 string"""
    if name == "Date":
        if not isinstance(value, datetime.datetime | datetime.date | str):
            raise ValueError(f"Invalid type for {name}: {type(value)}")
        elif isinstance(value, str):
            match = re.match(r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})", value)
            if not match:
                raise ValueError(f"Invalid {name} format, not matching regex")
            try:
                datetime.date(**{k: int(v) for k, v in match.groupdict().items()})
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


def validate_counter(name: str, _: str):
    """ensures Counter metadata is not manually set"""
    if name == "Counter":
        raise ValueError(f"{name} cannot be set. libzim sets it.")


def validate_description(name: str, value: str):
    """ensures Description metadata is with required length"""
    if (
        name == "Description"
        and nb_grapheme_for(value) > MAXIMUM_DESCRIPTION_METADATA_LENGTH
    ):
        raise ValueError(f"{name} is too long.")


def validate_longdescription(name: str, value: str):
    """ensures LongDescription metadata is with required length"""
    if (
        name == "LongDescription"
        and nb_grapheme_for(value) > MAXIMUM_LONG_DESCRIPTION_METADATA_LENGTH
    ):
        raise ValueError(f"{name} is too long.")


def validate_tags(name: str, value: Iterable[str] | str):
    """ensures Tags metadata is either one or a list of strings"""
    if name == "Tags" and (
        not isinstance(value, Iterable)
        or not all(isinstance(tag, str) for tag in value)
    ):
        raise ValueError(f"Invalid type(s) for {name}")
    if (
        name == "Tags"
        and not isinstance(value, str)
        and isinstance(value, Iterable)
        and len(set(value)) != len(list(value))
    ):
        raise ValueError(f"Duplicate tags are not valid: {value}")
    if name == "Tags" and isinstance(value, str):
        values = value.split(";")
        if len(set(values)) != len(list(values)):
            raise ValueError(f"Duplicate tags are not valid: {value}")


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
