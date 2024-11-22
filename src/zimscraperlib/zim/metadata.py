from __future__ import annotations

import base64
import datetime
import io
import re
from dataclasses import dataclass

import regex

from zimscraperlib.constants import (
    ILLUSTRATIONS_METADATA_RE,
    MAXIMUM_DESCRIPTION_METADATA_LENGTH,
    MAXIMUM_LONG_DESCRIPTION_METADATA_LENGTH,
    RECOMMENDED_MAX_TITLE_LENGTH,
)
from zimscraperlib.i18n import is_valid_iso_639_3
from zimscraperlib.image.probing import is_valid_image
from zimscraperlib.inputs import unique_values

# All control characters are disallowed in str metadata except \n, \r and \t
UNWANTED_CONTROL_CHARACTERS_REGEX = regex.compile(r"(?![\n\t\r])\p{C}")

# flag to enable / disable check conventions (e.g. title shorter than 30 chars,
# description shorter than 80 chars, ...)
check_metadata_conventions: bool = True


def clean_str(value: str) -> str:
    """Clean a string value for unwanted control characters and strip white chars"""
    return UNWANTED_CONTROL_CHARACTERS_REGEX.sub("", value).strip(" \r\n\t")


def nb_grapheme_for(value: str) -> int:
    """Number of graphemes (visually perceived characters) in a given string"""
    return len(regex.findall(r"\X", value))


class Metadata:
    """A very basic metadata, with a name and a bytes or io.BytesIO value

    Compliance with ZIM specification is done at initialisation, value passed at
    initialization is kept in memory in `value` attribute, target name is stored in
    `name` value and conversion to libzim value is available with `libzim_value`
    property.
    """

    def __init__(self, name: str, value: bytes | io.BytesIO) -> None:
        if not isinstance(value, bytes | io.BytesIO):
            raise ValueError(
                f"Unexpected type passed to {self.__class__.__qualname__}: "
                f"{value.__class__.__qualname__}"
            )
        if name == "Counter":
            raise ValueError("Counter cannot be set. libzim sets it.")
        self.name = name
        self.value = value
        libzim_value = self.libzim_value  # to check for errors
        if libzim_value is None or len(libzim_value) == 0:
            raise ValueError("Cannot set empty metadata")

    @property
    def libzim_value(self) -> bytes:
        """The value to pass to the libzim for creating the metadata"""
        if isinstance(self.value, io.BytesIO):
            return self.value.getvalue()
        return self.value


class _TextMetadata(Metadata):
    """A basic metadata whose value is expected to be some text"""

    def __init__(self, name: str, value: bytes | io.BytesIO | str) -> None:
        if not isinstance(value, bytes | io.BytesIO | str):
            raise ValueError(
                f"Unexpected type passed to {self.__class__.__qualname__}: "
                f"{value.__class__.__qualname__}"
            )
        super().__init__(
            name=name,
            value=(
                value.encode()
                if isinstance(value, str)
                else value.getvalue() if isinstance(value, io.BytesIO) else value
            ),
        )
        self.value = value
        _ = self.libzim_value  # to check for errors

    @property
    def libzim_value(self) -> bytes:
        """The value to pass to the libzim for creating the metadata"""
        # decode and reencode byte types to validate it's proper UTF-8 text
        if isinstance(self.value, io.BytesIO):
            str_value = self.value.getvalue().decode()
        elif isinstance(self.value, bytes):
            str_value = self.value.decode()
        else:
            str_value = self.value
        return clean_str(str_value).encode()


def _check_for_allowed_custom_metadata_name(name: str, class_name: str):
    """Check that metadata name is not among the standard ones for which a type exist"""
    if name in DEFAULT_DEV_ZIM_METADATA.__dict__.keys():
        # this list contains the 'bad' illustration keys, but we don't care, they should
        # still not be used
        raise ValueError(
            f"It is not allowed to use {class_name} for standard {name} "
            f"metadata. Please use {name}Metadata type for proper checks"
        )
    if name.startswith("Illustration_"):
        raise ValueError(
            f"It is not allowed to use {class_name} for standard Illustration"
            "metadata. Please use IllustrationMetadata type for proper checks"
        )


class CustomTextMetadata(_TextMetadata):
    """A text metadata for which we do little checks"""

    def __init__(self, name: str, value: bytes | io.BytesIO | str) -> None:
        _check_for_allowed_custom_metadata_name(name, self.__class__.__qualname__)
        super().__init__(name=name, value=value)


class CustomMetadata(Metadata):
    """A bytes metadata for which we do little checks"""

    def __init__(self, name: str, value: bytes | io.BytesIO) -> None:
        _check_for_allowed_custom_metadata_name(name, self.__class__.__qualname__)
        super().__init__(name=name, value=value)


class _MandatoryTextMetadata(_TextMetadata):
    """A mandatory (value must be set) text metadata"""

    @property
    def libzim_value(self) -> bytes:
        """The value to pass to the libzim for creating the metadata"""
        value = super().libzim_value
        if len(value) == 0:
            raise ValueError("Missing value for mandatory metadata")
        return value


class _MandatoryMetadata(Metadata):
    """A mandatory (value must be set) bytes metadata"""

    @property
    def libzim_value(self) -> bytes:
        """The value to pass to the libzim for creating the metadata"""
        value = super().libzim_value
        if len(value) == 0:
            raise ValueError("Missing value for mandatory metadata")
        return value


class TitleMetadata(_MandatoryTextMetadata):
    """The Title metadata"""

    def __init__(self, value: bytes | io.BytesIO | str) -> None:
        super().__init__(name="Title", value=value)

    @property
    def libzim_value(self) -> bytes:
        """The value to pass to the libzim for creating the metadata"""
        value = super().libzim_value
        if check_metadata_conventions:
            if nb_grapheme_for(value.decode()) > RECOMMENDED_MAX_TITLE_LENGTH:
                raise ValueError("Title is too long.")
        return value


class DescriptionMetadata(_MandatoryTextMetadata):
    """The Description metadata"""

    def __init__(self, value: bytes | io.BytesIO | str) -> None:
        super().__init__(name="Description", value=value)

    @property
    def libzim_value(self) -> bytes:
        """The value to pass to the libzim for creating the metadata"""
        value = super().libzim_value
        if check_metadata_conventions:
            if nb_grapheme_for(value.decode()) > MAXIMUM_DESCRIPTION_METADATA_LENGTH:
                raise ValueError("Description is too long.")
        return value


class LongDescriptionMetadata(_MandatoryTextMetadata):
    """The LongDescription metadata"""

    def __init__(self, value: bytes | io.BytesIO | str) -> None:
        super().__init__(name="LongDescription", value=value)

    @property
    def libzim_value(self) -> bytes:
        """The value to pass to the libzim for creating the metadata"""
        value = super().libzim_value
        if check_metadata_conventions:
            if (
                nb_grapheme_for(value.decode())
                > MAXIMUM_LONG_DESCRIPTION_METADATA_LENGTH
            ):
                raise ValueError("LongDescription is too long.")
        return value


class DateMetadata(_TextMetadata):
    """The Date metadata"""

    def __init__(self, value: bytes | str | datetime.date | datetime.datetime) -> None:
        if not isinstance(value, bytes | str | datetime.date | datetime.datetime):
            raise ValueError(
                f"Unexpected type passed to {self.__class__.__qualname__}: "
                f"{value.__class__.__qualname__}"
            )
        super().__init__(
            name="Date",
            value=(
                value
                if isinstance(value, bytes)
                else (
                    value.encode()
                    if isinstance(value, str)
                    else value.strftime("%Y-%m-%d").encode()
                )
            ),
        )
        self.value = value
        _ = self.libzim_value  # to check for errors

    @property
    def libzim_value(self) -> bytes:
        """The value to pass to the libzim for creating the metadata"""
        if isinstance(self.value, datetime.date | datetime.datetime):
            return self.value.strftime("%Y-%m-%d").encode()
        match = re.match(
            r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})",
            self.value.decode() if isinstance(self.value, bytes) else self.value,
        )
        if not match:
            raise ValueError("Invalid date format, not matching regex yyyy-mm-dd")
        try:
            datetime.date(**{k: int(v) for k, v in match.groupdict().items()})
        except Exception as exc:
            raise ValueError(f"Invalid date format: {exc}") from None
        return self.value if isinstance(self.value, bytes) else self.value.encode()


class IllustrationMetadata(_MandatoryMetadata):
    """Any Illustration_**x**@* metadata"""

    def __init__(self, name: str, value: bytes | io.BytesIO) -> None:
        super().__init__(name=name, value=value)
        _ = self.libzim_value  # to check for errors

    @property
    def libzim_value(self) -> bytes:
        """The value to pass to the libzim for creating the metadata"""
        match = ILLUSTRATIONS_METADATA_RE.match(self.name)
        if not match:
            raise ValueError("Illustration metadata has improper name")
        self.size = int(match.groupdict()["height"])
        if int(match.groupdict()["width"]) != self.size:
            raise ValueError("Illustration is not squared")
        if not is_valid_image(
            image=self.value,
            imformat="PNG",
            size=(self.size, self.size),
        ):
            raise ValueError(
                f"{self.name} is not a valid {self.size}x{self.size} PNG Image"
            )
        if isinstance(self.value, io.BytesIO):
            return self.value.getvalue()
        else:
            return self.value


class LanguageMetadata(_MandatoryTextMetadata):
    """The Language metadata"""

    def __init__(self, value: bytes | io.BytesIO | str | list[str] | set[str]) -> None:
        if not isinstance(value, bytes | io.BytesIO | str | list | set):
            raise ValueError(
                f"Unexpected type passed to {self.__class__.__qualname__}: "
                f"{value.__class__.__qualname__}"
            )
        if isinstance(value, list | set) and not all(
            isinstance(item, str) for item in value
        ):
            bad_types = {item.__class__.__qualname__ for item in value} - {"str"}
            raise ValueError(
                f"Invalid type(s) found in Iterable: {",".join(bad_types)}"
            )
        super().__init__(
            name="Language",
            value=",".join(value) if isinstance(value, list | set) else value,
        )
        self.value = value
        _ = self.libzim_value  # to check for errors

    @property
    def libzim_value(self) -> bytes:
        """The value to pass to the libzim for creating the metadata"""
        if isinstance(self.value, bytes | io.BytesIO | str):
            codes = [
                clean_str(code) for code in super().libzim_value.decode().split(",")
            ]
        else:
            codes = [clean_str(code) for code in self.value]
        codes = [code for code in codes if code]  # remove empty values
        if len(codes) == 0:
            raise ValueError("Missing value for mandatory Language metadata")
        if len(set(codes)) != len(codes):
            raise ValueError("Duplicate codes not allowed in Language metadata")
        for code in codes:
            if not is_valid_iso_639_3(code):
                raise ValueError(f"{code} is not ISO-639-3.")
        return ",".join(codes).encode()


class TagsMetadata(_TextMetadata):
    """The Tags metadata"""

    def __init__(self, value: bytes | io.BytesIO | str | list[str] | set[str]) -> None:
        if not isinstance(value, bytes | io.BytesIO | str | list | set):
            raise ValueError(
                f"Unexpected type passed to {self.__class__.__qualname__}: "
                f"{value.__class__.__qualname__}"
            )
        if isinstance(value, list | set) and not all(
            isinstance(item, str) for item in value
        ):
            bad_types = {item.__class__.__qualname__ for item in value} - {"str"}
            raise ValueError(
                f"Invalid type(s) found in Iterable: {",".join(bad_types)}"
            )
        super().__init__(
            name="Tags",
            value=";".join(value) if isinstance(value, list | set) else value,
        )
        self.value = value
        _ = self.libzim_value  # to check for errors

    @property
    def libzim_value(self) -> bytes:
        """The value to pass to the libzim for creating the metadata"""
        if isinstance(self.value, bytes | io.BytesIO | str):
            tags = unique_values(
                [clean_str(tag) for tag in super().libzim_value.decode().split(";")]
            )
        else:
            tags = unique_values([clean_str(tag) for tag in self.value])
        tags = [tag for tag in tags if tag]  # remove empty values
        return ";".join(tags).encode()


class NameMetadata(_MandatoryTextMetadata):
    """The Name metadata"""

    def __init__(self, value: bytes | io.BytesIO | str) -> None:
        super().__init__("Name", value)


class CreatorMetadata(_MandatoryTextMetadata):
    """The Creator metadata"""

    def __init__(self, value: bytes | io.BytesIO | str) -> None:
        super().__init__("Creator", value)


class PublisherMetadata(_MandatoryTextMetadata):
    """The Publisher metadata"""

    def __init__(self, value: bytes | io.BytesIO | str) -> None:
        super().__init__("Publisher", value)


class ScraperMetadata(_TextMetadata):
    """The Scraper metadata"""

    def __init__(self, value: bytes | io.BytesIO | str) -> None:
        super().__init__("Scraper", value)


class FlavourMetadata(_TextMetadata):
    """The Flavour metadata"""

    def __init__(self, value: bytes | io.BytesIO | str) -> None:
        super().__init__("Flavour", value)


class SourceMetadata(_TextMetadata):
    """The Source metadata"""

    def __init__(self, value: bytes | io.BytesIO | str) -> None:
        super().__init__("Source", value)


class LicenseMetadata(_TextMetadata):
    """The License metadata"""

    def __init__(self, value: bytes | io.BytesIO | str) -> None:
        super().__init__("License", value)


class RelationMetadata(_TextMetadata):
    """The Relation metadata"""

    def __init__(self, value: bytes | io.BytesIO | str) -> None:
        super().__init__("Relation", value)


@dataclass
class StandardMetadataList:
    """A class holding all openZIM standard metadata

    Useful to ensure that all mandatory metadata are set, no typo occurs in metadata
    name and the specification is respected (forbidden duplicate values, ...).
    """

    Name: NameMetadata
    Language: LanguageMetadata
    Title: TitleMetadata
    Creator: CreatorMetadata
    Publisher: PublisherMetadata
    Date: DateMetadata
    Illustration_48x48_at_1: IllustrationMetadata
    Description: DescriptionMetadata
    LongDescription: LongDescriptionMetadata | None = None
    Tags: TagsMetadata | None = None
    Scraper: ScraperMetadata | None = None
    Flavour: FlavourMetadata | None = None
    Source: SourceMetadata | None = None
    License: LicenseMetadata | None = None
    Relation: RelationMetadata | None = None

    def values(self) -> list[Metadata]:
        return [v for v in self.__dict__.values() if v]


# A sample standard metadata list, to be used for dev purposes when one does not care
# at all about metadata values ; this ensures all metadata are compliant with the spec
DEFAULT_DEV_ZIM_METADATA = StandardMetadataList(
    Name=NameMetadata("Test Name"),
    Title=TitleMetadata("Test Title"),
    Creator=CreatorMetadata("Test Creator"),
    Publisher=PublisherMetadata("Test Publisher"),
    Date=DateMetadata("2023-01-01"),
    Description=DescriptionMetadata("Test Description"),
    Language=LanguageMetadata("fra"),
    # blank 48x48 transparent PNG
    Illustration_48x48_at_1=IllustrationMetadata(
        "Illustration_48x48@1",
        base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAADAAAAAwAQMAAABtzGvEAAAAGXRFWHRTb2Z0d2FyZQBB"
            "ZG9iZSBJbWFnZVJlYWR5ccllPAAAAANQTFRFR3BMgvrS0gAAAAF0Uk5TAEDm2GYAAAAN"
            "SURBVBjTY2AYBdQEAAFQAAGn4toWAAAAAElFTkSuQmCC"
        ),
    ),
)

# list of mandatory metadata of the zim file, automatically computed
MANDATORY_ZIM_METADATA_KEYS = [
    metadata.name
    for metadata in DEFAULT_DEV_ZIM_METADATA.__dict__.values()
    if isinstance(metadata, _MandatoryTextMetadata | _MandatoryMetadata)
]
