import base64
import datetime
import io
from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import asdict, dataclass, fields
from itertools import filterfalse
from typing import Any, TypeVar

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
from zimscraperlib.typing import SupportsRead, SupportsSeekableRead

# All control characters are disallowed in str metadata except \n, \r and \t
UNWANTED_CONTROL_CHARACTERS_REGEX = regex.compile(r"(?![\n\t\r])\p{C}")

# whether to apply openZIM recommendations (see https://wiki.openzim.org/wiki/Metadata)
APPLY_RECOMMENDATIONS: bool = True

# TypeVar without any constraint
T = TypeVar("T")


class MetadataBase[T](ABC):
    """Base class for metadata

    Both generic (to accomodate any value type implemented in child classes) and
    abstract (because it has no idea how to compute the cleaned_value and libzim_value
    for any value type)
    """

    # name of the metadata (not its value)
    meta_name: str
    value: T

    # MIME type of the value
    meta_mimetype: str

    # whether metadata is required or not
    is_required: bool = False

    # str: text value must be cleaned-up
    require_text_cleanup: bool = False

    # whether an empty value is allowed or not
    empty_allowed: bool = False

    # str: whether text value must be under a certain length
    oz_max_length: int

    # list[str]: text values in list must be cleaned-up
    require_textlist_cleanup: bool = False

    # list[str]: whether duplicate values are allowed in a list of str
    duplicates_allowed: bool = False
    # list[str]: whether duplicate values are automatically removed
    require_deduplication: bool = False

    # list[str]: whether values in list must all be ISO-636-3 codes
    oz_only_iso636_3_allowed: bool = False

    join_list_with: str = " "  # , | ;

    illustration_size: int
    illustration_scale: int = 1

    # str, list[str]: whether text value must be encoded to UTF-8
    require_utf8_encoding: bool = False

    # wether Name is automatically X-prefixed
    oz_x_prefixed: bool = False
    # wether Name is prevented to clash with reserved names
    oz_x_protected: bool = False

    def __init__(
        self, value: Any, name: str | None = None, mimetype: str | None = None
    ) -> None:
        if name:
            self.meta_name = name
        if not getattr(self, "meta_name", ""):
            raise OSError("Metadata name missing")
        if mimetype:
            self.meta_mimetype = mimetype
        self.value = self.get_cleaned_value(value)
        self.validate()

    def get_mimetype(self) -> str:
        # explicitly set first
        return getattr(self, "meta_mimetype", "text/plain;charset=UTF-8")

    @property
    def mimetype(self) -> str:
        return self.get_mimetype()

    @staticmethod
    def matches_reserved_name(name: str) -> bool:
        if name in [field.name for field in fields(StandardMetadataList)]:
            return True
        # set by libzim
        if name == "Counter":
            return True
        return bool(ILLUSTRATIONS_METADATA_RE.match(name))

    def get_name(self) -> str:
        if getattr(self, "illustration_size", 0) and getattr(
            self, "illustration_scale", 0
        ):
            return (
                f"Illustration_{self.illustration_size}x{self.illustration_size}"
                f"@{self.illustration_scale}"
            )

        # X- prefix is recommendation for custom
        if (
            self.oz_x_protected
            and APPLY_RECOMMENDATIONS
            and not self.meta_name.startswith("X-")
            and self.matches_reserved_name(self.meta_name)
        ):
            raise ValueError("Custom metdata name must be X- prefixed")
        if (
            self.oz_x_prefixed
            and APPLY_RECOMMENDATIONS
            and not self.meta_name.startswith("X-")
        ):
            return f"X-{self.meta_name}"
        return self.meta_name

    @property
    def name(self) -> str:
        return self.get_name()

    @staticmethod
    def get_encoded(value: str) -> bytes:
        return value.encode()

    def validate(self) -> None:
        _ = self.name
        _ = self.libzim_value

    @abstractmethod
    def get_cleaned_value(self, value: Any) -> T: ...

    @property
    def libzim_value(self) -> bytes:
        return self.get_libzim_value()

    @abstractmethod
    def get_libzim_value(self) -> bytes: ...


# Alias for convenience when function accept any metadata
AnyMetadata = MetadataBase[Any]

# TypeVar bounded to subclasses of GenericMetadata, used by class decorators so that
# they properly accommodate to the class they are used on while still knowing they have
# access to all attributes of the MetadataBase class
U = TypeVar("U", bound=AnyMetadata)


def clean_str(value: str) -> str:
    """Clean a string value for unwanted control characters and strip white chars"""
    return UNWANTED_CONTROL_CHARACTERS_REGEX.sub("", value).strip(" \r\n\t")


def nb_grapheme_for(value: str) -> int:
    """Number of graphemes (visually perceived characters) in a given string"""
    return len(regex.findall(r"\X", value))


def mandatory(cls: type[U]):
    """Marks a Metadata mandatory: must be set to please Creator and cannot be empty"""
    cls.is_required = True
    cls.empty_allowed = False
    return cls


def allow_empty(cls: type[U]):
    """Whether input can be blank"""
    cls.empty_allowed = True
    return cls


def allow_duplicates(cls: type[U]):
    """Whether list input can accept duplicate values"""
    cls.duplicates_allowed = True
    return cls


def deduplicate(cls: type[U]):
    """Whether duplicates in list inputs should be reduced"""
    cls.duplicates_allowed = True
    cls.require_deduplication = True
    return cls


def only_lang_codes(cls: type[U]):
    """Whether list input should be checked to only accept ISO-639-1 codes"""
    cls.oz_only_iso636_3_allowed = True
    return cls


def x_protected(cls: type[U]):
    """Whether metadata name should be checked for collision with reserved names

    when applying recommendations"""
    cls.oz_x_protected = True
    return cls


def x_prefixed(cls: type[U]):
    """Whether metadata names should be automatically X-Prefixed"""
    cls.oz_x_protected = False
    cls.oz_x_prefixed = True
    return cls


class Metadata(MetadataBase[bytes]):

    def get_binary_from(
        self,
        value: bytes | SupportsRead[bytes] | SupportsSeekableRead[bytes] | io.BytesIO,
    ) -> bytes:
        bvalue: bytes = b""
        if isinstance(value, io.BytesIO):
            bvalue = value.getvalue()
        elif isinstance(value, bytes):
            bvalue = value
        else:
            last_pos: int = 0
            if isinstance(value, SupportsSeekableRead) and value.seekable():
                last_pos = value.tell()
            bvalue = value.read()
            if isinstance(value, SupportsSeekableRead) and value.seekable():
                value.seek(last_pos)
        if not self.empty_allowed and not value:
            raise ValueError("Missing value (empty not allowed)")
        return bvalue

    # native type is bytes
    def get_cleaned_value(self, value: bytes | io.IOBase | io.BytesIO) -> bytes:
        return self.get_binary_from(value)

    def get_libzim_value(self) -> bytes:
        return self.value


class TextBasedMetadata(MetadataBase[str]):
    """Expects a Text (str) input. Will be cleaned-up and UTF-8 encoded"""

    value: str
    require_text_cleanup = True
    require_utf8_encoding = True

    def __init__(self, value: str, name: str | None = None) -> None:
        super().__init__(value=value, name=name)

    # native type is str
    def get_cleaned_value(self, value: str) -> str:
        if self.require_text_cleanup:
            value = clean_str(value)

        if not self.empty_allowed and not value.strip():
            raise ValueError("Missing value (empty not allowed)")

        # max-length is openZIM recommendation
        if getattr(self, "oz_max_length", 0) and APPLY_RECOMMENDATIONS:
            if nb_grapheme_for(value) > self.oz_max_length:
                raise ValueError(
                    f"{self.name} value is too long ({self.oz_max_length})"
                )
        return value

    def get_libzim_value(self) -> bytes:
        return self.get_encoded(self.value)


class TextListBasedMetadata(MetadataBase[list[str]]):
    """Expects a Text List (list[str]) input. Each item will be cleaned-up.

    List will be joined (see `join_list_with`) and UTF-8 encoded"""

    value: list[str]  # we accept single str input but store as list[str]
    require_textlist_cleanup = True
    require_utf8_encoding = True

    def __init__(self, value: Iterable[str] | str, name: str | None = None) -> None:
        super().__init__(value=value, name=name)

    # native type is list[str]
    def get_cleaned_value(self, value: Iterable[str] | str) -> list[str]:
        if isinstance(value, str):
            value = [value]
        else:
            value = list(value)
        if self.require_textlist_cleanup:
            value = [clean_str(item) for item in value]
        if not self.empty_allowed and (not value or not all(value)):
            raise ValueError("Missing value (empty not allowed)")
        if not self.duplicates_allowed and len(set(value)) != len(value):
            raise ValueError("Duplicate entries not allowed")
        elif self.require_deduplication:
            value = unique_values(value)
        if self.oz_only_iso636_3_allowed and APPLY_RECOMMENDATIONS:
            invalid_codes = list(filterfalse(is_valid_iso_639_3, value))
            if invalid_codes:
                raise ValueError(
                    f"Following code(s) are not ISO-639-3: {','.join(invalid_codes)}"
                )
        return value

    def get_libzim_value(self) -> bytes:
        return self.get_encoded(self.join_list_with.join(self.value))


class DateBasedMetadata(MetadataBase[datetime.date]):
    """Expects a Date (date | datetime) input. Will be UTF-8 encoded as YYYY-MM-DD"""

    value: datetime.date
    require_utf8_encoding = True

    def __init__(
        self, value: datetime.date | datetime.datetime, name: str | None = None
    ) -> None:
        super().__init__(value=value, name=name)

    # native type is date
    def get_cleaned_value(self, value: datetime.date) -> datetime.date:
        if isinstance(value, datetime.datetime):
            value = value.date()
        return value

    def get_libzim_value(self) -> bytes:
        return self.get_encoded(self.value.strftime("%Y-%m-%d"))


class IllustrationBasedMetadata(Metadata):
    """Expects a Square PNG Illustration (bytes-like) input.

    PNG format and squareness will be checked"""

    value: bytes
    meta_mimetype = "image/png"

    def __init__(
        self, value: bytes | io.IOBase | io.BytesIO, name: str | None = None
    ) -> None:
        super().__init__(value=value, name=name)

    # native type is PNG image buffer
    def get_cleaned_value(self, value: bytes | io.IOBase | io.BytesIO) -> bytes:
        value = self.get_binary_from(value)
        if not is_valid_image(
            image=value,
            imformat="PNG",
            size=(self.illustration_size, self.illustration_size),
        ):
            raise ValueError(
                f"{self.name} is not a valid "
                f"{self.illustration_size}x{self.illustration_size} PNG Image"
            )
        return value

    def get_libzim_value(self) -> bytes:
        return self.value


@mandatory
class NameMetadata(TextBasedMetadata):
    meta_name: str = "Name"


@mandatory
@only_lang_codes
class LanguageMetadata(TextListBasedMetadata):
    meta_name: str = "Language"
    join_list_with: str = ","


@mandatory
class TitleMetadata(TextBasedMetadata):
    meta_name: str = "Title"
    oz_max_length: int = RECOMMENDED_MAX_TITLE_LENGTH


@mandatory
class CreatorMetadata(TextBasedMetadata):
    meta_name: str = "Creator"


@mandatory
class PublisherMetadata(TextBasedMetadata):
    meta_name: str = "Publisher"


@mandatory
class DateMetadata(DateBasedMetadata):
    meta_name: str = "Date"


class IllustrationMetadata(IllustrationBasedMetadata):
    meta_name = "Illustration_{size}x{size}@{scale}"
    illustration_size: int
    illustration_scale: int = 1

    def __init__(
        self, value: bytes | io.IOBase | io.BytesIO, size: int, scale: int = 1
    ) -> None:
        self.illustration_scale = scale
        self.illustration_size = size
        super().__init__(value=value)


@mandatory
class DefaultIllustrationMetadata(IllustrationBasedMetadata):
    meta_name = "Illustration_48x48@1"
    illustration_size: int = 48
    illustration_scale: int = 1


@mandatory
class DescriptionMetadata(TextBasedMetadata):
    meta_name: str = "Description"
    oz_max_length: int = MAXIMUM_DESCRIPTION_METADATA_LENGTH


class LongDescriptionMetadata(TextBasedMetadata):
    meta_name: str = "LongDescription"
    oz_max_length: int = MAXIMUM_LONG_DESCRIPTION_METADATA_LENGTH


@deduplicate
class TagsMetadata(TextListBasedMetadata):
    meta_name: str = "Tags"
    join_list_with: str = ";"


class ScraperMetadata(TextBasedMetadata):
    meta_name: str = "Scraper"


class FlavourMetadata(TextBasedMetadata):
    meta_name: str = "Flavour"


class SourceMetadata(TextBasedMetadata):
    meta_name: str = "Source"


class LicenseMetadata(TextBasedMetadata):
    meta_name: str = "License"


class RelationMetadata(TextBasedMetadata):
    meta_name: str = "Relation"


@dataclass
class StandardMetadataList:

    Name: NameMetadata
    Language: LanguageMetadata
    Title: TitleMetadata
    Creator: CreatorMetadata
    Publisher: PublisherMetadata
    Date: DateMetadata
    Illustration_48x48_at_1: DefaultIllustrationMetadata
    Description: DescriptionMetadata
    LongDescription: LongDescriptionMetadata | None = None
    Tags: TagsMetadata | None = None
    Scraper: ScraperMetadata | None = None
    Flavour: FlavourMetadata | None = None
    Source: SourceMetadata | None = None
    License: LicenseMetadata | None = None
    Relation: RelationMetadata | None = None

    def values(self) -> list[AnyMetadata]:
        return list(filter(bool, asdict(self).values()))

    @classmethod
    def get_reserved_names(cls) -> list[str]:
        """list of mandatory metadata as per the spec.

        computed from metadata using @mandatory decorator"""
        names: list[str] = []
        for field in fields(cls):
            if not isinstance(field.type, type):
                continue
            # field.type is a `type` only when expecting a single type
            # and is a string in case of None Union
            names.append(getattr(field.type, "meta_name", ""))
        return names


@x_protected
class CustomMetadata(Metadata):
    def __init__(self, name: str, value: bytes | io.IOBase | io.BytesIO) -> None:
        self.meta_name = name
        super().__init__(value=value)


@x_protected
class CustomTextMetadata(TextBasedMetadata):
    def __init__(self, name: str, value: str) -> None:
        self.meta_name = name
        super().__init__(name=name, value=value)


@x_prefixed
class XCustomMetadata(CustomMetadata):
    # reimpl just to please coverage
    def __init__(self, name: str, value: bytes | io.IOBase | io.BytesIO) -> None:
        super().__init__(name=name, value=value)


@x_prefixed
class XCustomTextMetadata(CustomTextMetadata):
    # reimpl just to please coverage
    def __init__(self, name: str, value: str) -> None:
        super().__init__(name=name, value=value)


MANDATORY_ZIM_METADATA_KEYS: list[str] = StandardMetadataList.get_reserved_names()


DEFAULT_DEV_ZIM_METADATA = StandardMetadataList(
    Name=NameMetadata("Test Name"),
    Title=TitleMetadata("Test Title"),
    Creator=CreatorMetadata("Test Creator"),
    Publisher=PublisherMetadata("Test Publisher"),
    Date=DateMetadata(datetime.date(2023, 1, 1)),
    Description=DescriptionMetadata("Test Description"),
    Language=LanguageMetadata("fra"),
    # blank 48x48 transparent PNG
    Illustration_48x48_at_1=DefaultIllustrationMetadata(
        base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAADAAAAAwAQMAAABtzGvEAAAAGXRFWHRTb2Z0d2FyZQBB"
            "ZG9iZSBJbWFnZVJlYWR5ccllPAAAAANQTFRFR3BMgvrS0gAAAAF0Uk5TAEDm2GYAAAAN"
            "SURBVBjTY2AYBdQEAAFQAAGn4toWAAAAAElFTkSuQmCC"
        ),
    ),
)
