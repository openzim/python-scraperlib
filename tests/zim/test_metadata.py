from __future__ import annotations

import base64
import dataclasses
import datetime
import io
import pathlib
import re
from typing import NamedTuple

import pytest

from zimscraperlib.zim import metadata


@pytest.mark.parametrize(
    "value",
    [
        ("fra"),
        ("eng"),
        ("bam"),
        ("fra,eng"),
        ("eng, fra"),
        ("fra,eng,bam"),
        (["fra", "eng"]),
        ("fra, eng"),  # codes are automatically cleaned-up
        ("eng,  \r"),  # codes are automatically cleaned-up
        (["fra", "  "]),  # codes are automatically cleaned-up
    ],
)
def test_validate_language_valid(value: list[str] | str):
    assert metadata.LanguageMetadata(value)


@pytest.mark.parametrize(
    "value,error",
    [
        ("", "Missing value for mandatory metadata"),
        ("fr", "is not ISO-639-3"),
        ("en", "is not ISO-639-3"),
        ("xxx", "is not ISO-639-3"),
        ("rmr", "is not ISO-639-3"),
        ("fra,en,bam", "is not ISO-639-3"),
        ("fra;eng", "is not ISO-639-3"),
        ("fra,fra", "Duplicate codes not allowed in Language metadata"),
        (["fra", "fra"], "Duplicate codes not allowed in Language metadata"),
        ([], "Missing value for mandatory metadata"),
        (["  ", "\t"], "Missing value for mandatory Language metadata"),
        ("  , ", "Missing value for mandatory Language metadata"),
        (["fra", 1], "Invalid type(s) found in Iterable:"),
        (["fra", b"1"], "Invalid type(s) found in Iterable:"),
        (["fra", 1, b"1"], "Invalid type(s) found in Iterable:"),
    ],
)
def test_validate_language_invalid(value: list[str] | str, error: str):
    with pytest.raises(ValueError, match=re.escape(error)):
        assert metadata.LanguageMetadata(value)


@pytest.mark.parametrize(
    "tags, is_valid",
    [
        pytest.param("wikipedia", True, id="simple_tag"),
        pytest.param("taaaag1", True, id="many_letters"),
        pytest.param("wikipedia;   ", True, id="remove_empty_values"),
        pytest.param("wikipedia ;  football", True, id="semi_colon_distinct_1"),
        pytest.param("football;football", True, id="semi_colon_identical"),
        pytest.param("tag,1;tug,1", True, id="semi_colon_distinct_2"),
        pytest.param(
            "wikipedia,football", True, id="comma"
        ),  # we cannot say that this ought to be a tags separator
        pytest.param({"wikipedia"}, True, id="one_tag_in_set"),
        pytest.param({"wikipedia", "football"}, True, id="two_tags_in_set"),
        pytest.param(["wikipedia", "football"], True, id="two_distinct"),
        pytest.param(["wikipedia", "wikipedia"], True, id="two_identical"),
    ],
)
def test_validate_tags_valid(tags, is_valid):
    if is_valid:
        metadata.TagsMetadata(tags)
    else:
        with pytest.raises((ValueError, TypeError)):
            metadata.TagsMetadata(tags)


@pytest.mark.parametrize(
    "value, error",
    [
        pytest.param("", "Cannot set empty metadata", id="empty_string"),
        pytest.param(1, "Unexpected type passed to TagsMetadata: int", id="one_int"),
        pytest.param(
            None, "Unexpected type passed to TagsMetadata: NoneType", id="none_value"
        ),
        pytest.param(
            ["wikipedia", 1], "Invalid type(s) found in Iterable: int", id="int_in_list"
        ),
    ],
)
def test_validate_tags_invalid(value: list[str] | str, error: str):
    with pytest.raises(ValueError, match=re.escape(error)):
        metadata.TagsMetadata(value)


def test_validate_dedup_tags():
    assert (
        metadata.TagsMetadata("  wikipedia  \t   ;   wikipedia").libzim_value
        == b"wikipedia"
    )


def test_validate_short_title_check_enabled():
    assert metadata.TitleMetadata("T" * 30)


def test_validate_short_grapheme_title_check_enabled():
    assert metadata.TitleMetadata("में" * 30)


def test_validate_too_long_title_check_enabled():
    with pytest.raises(ValueError, match="Title is too long"):
        assert metadata.TitleMetadata("T" * 31)


def test_validate_too_long_title_check_disabled(
    ignore_metadata_conventions,  # noqa: ARG001
):
    assert metadata.TitleMetadata("T" * 31)


def test_validate_short_description_check_enabled():
    assert metadata.DescriptionMetadata("T" * 80)


def test_validate_short_grapheme_description_check_enabled():
    assert metadata.DescriptionMetadata("में" * 80)


def test_validate_too_long_description_check_enabled():
    with pytest.raises(ValueError, match="Description is too long"):
        assert metadata.DescriptionMetadata("T" * 81)


def test_validate_too_long_description_check_disabled(
    ignore_metadata_conventions,  # noqa: ARG001
):
    assert metadata.DescriptionMetadata("T" * 81)


def test_validate_short_longdescription_check_enabled():
    assert metadata.LongDescriptionMetadata("T" * 4000)


def test_validate_short_grapheme_longdescription_check_enabled():
    assert metadata.LongDescriptionMetadata("में" * 4000)


def test_validate_too_long_longdescription_check_enabled():
    with pytest.raises(ValueError, match="Description is too long"):
        assert metadata.LongDescriptionMetadata("T" * 4001)


def test_validate_too_long_longdescription_check_disabled(
    ignore_metadata_conventions,  # noqa: ARG001
):
    assert metadata.LongDescriptionMetadata("T" * 4001)


def test_validate_date_datetime_date():
    assert metadata.DateMetadata(datetime.date(2024, 12, 11))


def test_validate_date_datetime_datetime():
    assert metadata.DateMetadata(
        datetime.datetime(2024, 12, 11, 0, 0, 0, tzinfo=datetime.UTC)
    )


@pytest.mark.parametrize("value", [("9999-99-99"), ("2023/02/29"), ("1969-13-31")])
def test_validate_date_invalid_date(value):
    with pytest.raises(ValueError, match="Invalid date format"):
        metadata.DateMetadata(value)


def test_validate_illustration_invalid_name():
    with pytest.raises(ValueError, match="Illustration metadata has improper name"):
        metadata.IllustrationMetadata("Illustration_48x48_at_1", b"")


def test_validate_illustration_not_squared():
    with pytest.raises(ValueError, match="Illustration is not squared"):
        metadata.IllustrationMetadata("Illustration_48x96@1", b"")


def test_validate_illustration_wrong_sizes(png_image2):
    with open(png_image2, "rb") as fh:
        png_data = fh.read()
    with pytest.raises(
        ValueError, match="Illustration_48x48@1 is not a valid 48x48 PNG Image"
    ):
        metadata.IllustrationMetadata("Illustration_48x48@1", png_data)


def test_blank_metadata():
    with pytest.raises(ValueError, match="Cannot set empty metadata"):
        metadata.Metadata("Blank", b"")


class MetadataInitConfig(NamedTuple):
    a_type: type
    nb_args: int


@pytest.fixture(
    params=[
        MetadataInitConfig(metadata.Metadata, 2),
        MetadataInitConfig(metadata._TextMetadata, 2),
        MetadataInitConfig(metadata.CustomTextMetadata, 2),
        MetadataInitConfig(metadata.CustomMetadata, 2),
        MetadataInitConfig(metadata._MandatoryTextMetadata, 2),
        MetadataInitConfig(metadata._MandatoryMetadata, 2),
        MetadataInitConfig(metadata.TitleMetadata, 1),
        MetadataInitConfig(metadata.DescriptionMetadata, 1),
        MetadataInitConfig(metadata.LongDescriptionMetadata, 1),
        MetadataInitConfig(metadata.DateMetadata, 1),
        MetadataInitConfig(metadata.IllustrationMetadata, 2),
        MetadataInitConfig(metadata.LanguageMetadata, 1),
        MetadataInitConfig(metadata.TagsMetadata, 1),
        MetadataInitConfig(metadata.NameMetadata, 1),
        MetadataInitConfig(metadata.CreatorMetadata, 1),
        MetadataInitConfig(metadata.PublisherMetadata, 1),
        MetadataInitConfig(metadata.ScraperMetadata, 1),
        MetadataInitConfig(metadata.FlavourMetadata, 1),
        MetadataInitConfig(metadata.SourceMetadata, 1),
        MetadataInitConfig(metadata.LicenseMetadata, 1),
        MetadataInitConfig(metadata.RelationMetadata, 1),
    ]
)
def metadata_init(request: pytest.FixtureRequest) -> MetadataInitConfig:
    return request.param


def test_none_metadata_two_args(metadata_init: MetadataInitConfig):
    with pytest.raises(
        ValueError,
        match=f"Unexpected type passed to {metadata_init.a_type.__name__}: NoneType",
    ):
        if metadata_init.nb_args == 2:
            metadata_init.a_type(
                "Foo",
                None,  # pyright: ignore[reportArgumentType]
            )
        elif metadata_init.nb_args == 1:
            metadata_init.a_type(None)


@pytest.mark.parametrize(
    "a_type",
    [
        (metadata.Metadata),
        (metadata.CustomTextMetadata),
        (metadata._TextMetadata),
        (metadata._MandatoryMetadata),
    ],
)
def test_reserved_counter_metadata(a_type: type):
    with pytest.raises(ValueError, match="Counter cannot be set. libzim sets it."):
        a_type("Counter", b"Foo")


@pytest.mark.parametrize(
    "metadata_name",
    [
        ("Name"),
        ("Language"),
        ("Title"),
        ("Creator"),
        ("Publisher"),
        ("Date"),
        ("Illustration_48x48@1"),
        ("Illustration_96x96@1"),
        ("Description"),
        ("LongDescription"),
        ("Tags"),
        ("Scraper"),
        ("Flavour"),
        ("Source"),
        ("License"),
        ("Relation"),
    ],
)
@pytest.mark.parametrize(
    "metadata_type",
    [
        (metadata.CustomMetadata),
        (metadata.CustomTextMetadata),
    ],
)
def test_reserved_names(metadata_name: str, metadata_type: type):
    with pytest.raises(ValueError, match="It is not allowed to use"):
        metadata_type(metadata_name, b"a value")


def test_mandatory_value(metadata_init: MetadataInitConfig):

    with pytest.raises(
        ValueError,
        match=(
            "is not a valid 48x48 PNG Image"
            if metadata_init.a_type == metadata.IllustrationMetadata
            else (
                "Invalid date format, not matching regex"
                if metadata_init.a_type == metadata.DateMetadata
                else "Cannot set empty metadata|Missing value for mandatory metadata"
            )
        ),
    ):
        if metadata_init.nb_args == 2:
            metadata_init.a_type(
                (
                    "Foo"
                    if metadata_init.a_type != metadata.IllustrationMetadata
                    else "Illustration_48x48@1"
                ),
                b"",
            )
        elif metadata_init.nb_args == 1:
            metadata_init.a_type(b"")


def test_clean_value(metadata_init: MetadataInitConfig):
    raw_value = b"\t\n\r\n \tA val \t\awith  \bcontrol chars\v\n"
    clean_value = b"A val \twith  control chars"
    if metadata_init.a_type in (
        # some types do not support the raw value
        metadata.IllustrationMetadata,
        metadata.LanguageMetadata,
        metadata.DateMetadata,
        # and binary types are not cleaned-up
        metadata.Metadata,
        metadata.CustomMetadata,
        metadata._MandatoryMetadata,
    ):
        pytest.skip("unsupported configuration")  # ignore these test cases
    if metadata_init.nb_args == 2:
        assert metadata_init.a_type(("Foo"), raw_value).libzim_value == clean_value
    elif metadata_init.nb_args == 1:
        assert metadata_init.a_type(raw_value).libzim_value == clean_value


# @pytest.mark.parametrize(
#     "metadata, expected_value",
#     [
#         (metadata.Metadata("Foo", b"a value"), b"a value"),
#         (metadata.Metadata("Foo", io.BytesIO(b"a value")), b"a value"),
#         (metadata.DescriptionMetadata(io.BytesIO(b"a value")), b"a value"),
#         (metadata.DescriptionMetadata(b"a value"), b"a value"),
#         (metadata.DescriptionMetadata("a value"), b"a value"),
#         (metadata.IllustrationMetadata(png), b"a value"),
#     ],
# )
def test_libzim_bytes_value(metadata_init: MetadataInitConfig, png_image: pathlib.Path):
    if metadata_init.nb_args == 2:
        if metadata_init.a_type == metadata.IllustrationMetadata:
            with open(png_image, "rb") as fh:
                png_data = fh.read()
            assert (
                metadata.IllustrationMetadata(
                    "Illustration_48x48@1", png_data
                ).libzim_value
                == png_data
            )
        else:
            assert metadata_init.a_type("Foo", b"a value").libzim_value == b"a value"
    elif metadata_init.nb_args == 1:
        if metadata_init.a_type == metadata.DateMetadata:
            assert metadata_init.a_type(b"2023-12-11").libzim_value == b"2023-12-11"
        elif metadata_init.a_type == metadata.LanguageMetadata:
            assert metadata_init.a_type(b"fra,eng").libzim_value == b"fra,eng"
        else:
            assert metadata_init.a_type(b"a value").libzim_value == b"a value"


def test_libzim_io_bytesio_value(
    metadata_init: MetadataInitConfig, png_image: pathlib.Path
):
    if metadata_init.nb_args == 2:
        if metadata_init.a_type == metadata.IllustrationMetadata:
            with open(png_image, "rb") as fh:
                png_data = fh.read()
            assert (
                metadata.IllustrationMetadata(
                    "Illustration_48x48@1", io.BytesIO(png_data)
                ).libzim_value
                == png_data
            )
        else:
            assert (
                metadata_init.a_type("Foo", io.BytesIO(b"a value")).libzim_value
                == b"a value"
            )
    elif metadata_init.nb_args == 1:
        if metadata_init.a_type == metadata.DateMetadata:
            pass  # Not supported
        elif metadata_init.a_type == metadata.LanguageMetadata:
            assert (
                metadata_init.a_type(io.BytesIO(b"fra,eng")).libzim_value == b"fra,eng"
            )
        else:
            assert (
                metadata_init.a_type(io.BytesIO(b"a value")).libzim_value == b"a value"
            )


def test_std_metadata_values():
    test_value = dataclasses.replace(metadata.DEFAULT_DEV_ZIM_METADATA)
    test_value.License = metadata.LicenseMetadata("Creative Commons CC0")
    values = test_value.values()
    assert len(values) == 9

    expected_values: list[metadata.Metadata] = [
        metadata.LicenseMetadata("Creative Commons CC0"),
        metadata.NameMetadata("Test Name"),
        metadata.TitleMetadata("Test Title"),
        metadata.CreatorMetadata("Test Creator"),
        metadata.PublisherMetadata("Test Publisher"),
        metadata.DateMetadata("2023-01-01"),
        metadata.DescriptionMetadata("Test Description"),
        metadata.LanguageMetadata("fra"),
        # blank 48x48 transparent PNG
        metadata.IllustrationMetadata(
            "Illustration_48x48@1",
            base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAADAAAAAwAQMAAABtzGvEAAAAGXRFWHRTb2Z0d2FyZQBB"
                "ZG9iZSBJbWFnZVJlYWR5ccllPAAAAANQTFRFR3BMgvrS0gAAAAF0Uk5TAEDm2GYAAAAN"
                "SURBVBjTY2AYBdQEAAFQAAGn4toWAAAAAElFTkSuQmCC"
            ),
        ),
    ]
    for value in values:
        found = False
        for expected_value in expected_values:
            if value.__class__ == expected_value.__class__:
                assert value.value == expected_value.value
                found = True
                break
        if not found:
            pytest.fail(
                f"Did not found matching expected values for {value.name} metadata"
            )
