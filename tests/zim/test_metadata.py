import base64
import dataclasses
import datetime
import io
import pathlib
import re
from collections.abc import Iterable
from types import NoneType
from typing import BinaryIO, NamedTuple

import pytest
from beartype.roar import BeartypeCallHintParamViolation as InvalidType

from zimscraperlib.zim import metadata


def get_classvar_value_type(cls: type) -> type:
    """expected type of value classvar for a Metadata type

    Found in class annotations of type or any of its parent class"""
    target = cls
    while target:
        if value_type := getattr(target, "__annotations__", {}).get("value", False):
            return value_type
        target = getattr(target, "__base__", None)
    return NoneType


@pytest.mark.parametrize(
    "value",
    [
        ("fra"),
        ("eng"),
        ("bam"),
        (["fra", "eng"]),
        ("eng", "fra"),
        ("fra", "eng", "bam"),
        (["fra", "eng"]),
        ("fra", "eng"),  # codes are automatically cleaned-up
        ("eng\r"),  # codes are automatically cleaned-up
        (["fra "]),  # codes are automatically cleaned-up
    ],
)
def test_validate_language_valid(value: list[str] | str):
    assert metadata.LanguageMetadata(value)


@pytest.mark.parametrize(
    "value,exception,error",
    [
        ("", ValueError, "Missing value (empty not allowed)"),
        ("fr", ValueError, "are not ISO-639-3"),
        ("en", ValueError, "are not ISO-639-3"),
        ("xxx", ValueError, "are not ISO-639-3"),
        ("rmr", ValueError, "are not ISO-639-3"),
        ("fra,en,bam", ValueError, "are not ISO-639-3"),
        (("fra", "en", "bam"), ValueError, "are not ISO-639-3"),
        ("fra;eng", ValueError, "are not ISO-639-3"),
        (("fra", "fra"), ValueError, "Duplicate entries not allowed"),
        (["fra", "fra"], ValueError, "Duplicate entries not allowed"),
        ([], ValueError, "Missing value (empty not allowed)"),
        (["  ", "\t"], ValueError, "Missing value (empty not allowed)"),
        (("  ", " "), ValueError, "Missing value (empty not allowed)"),
        (["fra", 1], InvalidType, " violates type"),
        (["fra", b"1"], InvalidType, " violates type"),
        (["fra", 1, b"1"], InvalidType, " violates type"),
    ],
)
def test_validate_language_invalid(value: list[str] | str, exception: type, error: str):
    with pytest.raises(exception, match=re.escape(error)):
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
def test_validate_tags_valid(tags: Iterable[str] | str, *, is_valid: bool):
    if is_valid:
        metadata.TagsMetadata(tags)
    else:
        with pytest.raises((ValueError, TypeError)):
            metadata.TagsMetadata(tags)


@pytest.mark.parametrize(
    "value, exception, error",
    [
        pytest.param(
            "", ValueError, "Missing value (empty not allowed)", id="empty_string"
        ),
        pytest.param(1, InvalidType, " violates type", id="one_int"),
        pytest.param(
            None,
            InvalidType,
            " violates type",
            id="none_value",
        ),
        pytest.param(["wikipedia", 1], InvalidType, " violates type", id="int_in_list"),
    ],
)
def test_validate_tags_invalid(
    value: list[str] | str | int, exception: type, error: str
):
    with pytest.raises(exception, match=re.escape(error)):
        metadata.TagsMetadata(value)  # pyright: ignore[reportArgumentType]


def test_validate_dedup_tags():
    assert (
        metadata.TagsMetadata(["  wikipedia  \t   ", "   wikipedia"]).libzim_value
        == b"wikipedia"
    )


def test_validate_short_title_check_enabled():
    assert metadata.TitleMetadata("T" * 30)


def test_validate_short_grapheme_title_check_enabled():
    assert metadata.TitleMetadata("में" * 30)


def test_validate_too_long_title_check_enabled():
    with pytest.raises(ValueError, match="Title value is too long"):
        assert metadata.TitleMetadata("T" * 31)


def test_validate_too_long_title_check_disabled(
    ignore_metadata_conventions: NoneType,  # noqa: ARG001
):
    assert metadata.TitleMetadata("T" * 31)


def test_validate_short_description_check_enabled():
    assert metadata.DescriptionMetadata("T" * 80)


def test_validate_short_grapheme_description_check_enabled():
    assert metadata.DescriptionMetadata("में" * 80)


def test_validate_too_long_description_check_enabled():
    with pytest.raises(ValueError, match="Description value is too long"):
        assert metadata.DescriptionMetadata("T" * 81)


def test_validate_too_long_description_check_disabled(
    ignore_metadata_conventions: NoneType,  # noqa: ARG001
):
    assert metadata.DescriptionMetadata("T" * 81)


def test_validate_short_longdescription_check_enabled():
    assert metadata.LongDescriptionMetadata("T" * 4000)


def test_validate_short_grapheme_longdescription_check_enabled():
    assert metadata.LongDescriptionMetadata("में" * 4000)


def test_validate_too_long_longdescription_check_enabled():
    with pytest.raises(ValueError, match="LongDescription value is too long"):
        assert metadata.LongDescriptionMetadata("T" * 4001)


def test_validate_too_long_longdescription_check_disabled(
    ignore_metadata_conventions: NoneType,  # noqa: ARG001
):
    assert metadata.LongDescriptionMetadata("T" * 4001)


def test_validate_date_datetime_date():
    assert metadata.DateMetadata(datetime.date(2024, 12, 11))


def test_validate_date_datetime_datetime():
    assert metadata.DateMetadata(
        datetime.datetime(2024, 12, 11, 0, 0, 0, tzinfo=datetime.UTC)
    )


def test_validate_date_invalid_datee():
    assert metadata.DateMetadata(
        datetime.datetime(9, 12, 11, 0, 0, 0, tzinfo=datetime.UTC)
    )


@pytest.mark.parametrize("value", [("9999-99-99"), ("2023/02/29"), ("1969-13-31")])
def test_validate_date_invalid_datetype(value: str):
    with pytest.raises(InvalidType, match="violates type hint"):
        metadata.DateMetadata(value)  # pyright: ignore[reportArgumentType]


def test_validate_illustration_invalid_image():
    with pytest.raises(
        ValueError, match="Illustration_48x48@1 is not a valid 48x48 PNG Image"
    ):
        metadata.IllustrationMetadata(b"PN", size=48)


def test_validate_illustration_wrong_sizes(png_image2: pathlib.Path):
    with open(png_image2, "rb") as fh:
        png_data = fh.read()
    with pytest.raises(
        ValueError, match="Illustration_48x48@1 is not a valid 48x48 PNG Image"
    ):
        metadata.IllustrationMetadata(png_data, size=48)


def test_blank_metadata():
    with pytest.raises(ValueError, match=r"Missing value \(empty not allowed\)"):
        metadata.Metadata(name="Blank", value=b"")


class MetadataInitConfig(NamedTuple):
    a_type: type
    nb_args: int


@pytest.fixture(
    params=[
        MetadataInitConfig(metadata.Metadata, 2),
        MetadataInitConfig(metadata.CustomTextMetadata, 2),
        MetadataInitConfig(metadata.CustomMetadata, 2),
        MetadataInitConfig(metadata.XCustomMetadata, 2),
        MetadataInitConfig(metadata.XCustomTextMetadata, 2),
        MetadataInitConfig(metadata.TitleMetadata, 1),
        MetadataInitConfig(metadata.DescriptionMetadata, 1),
        MetadataInitConfig(metadata.LongDescriptionMetadata, 1),
        MetadataInitConfig(metadata.DateMetadata, 1),
        MetadataInitConfig(metadata.DefaultIllustrationMetadata, 1),
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
        ("Counter"),
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
    with pytest.raises(ValueError, match="Custom metdata name must be X- prefixed"):
        value = "x" if metadata_type == metadata.CustomTextMetadata else b"x"
        metadata_type(name=metadata_name, value=value)


@pytest.mark.parametrize(
    "metadata_name",
    [
        ("Nameo"),
        ("Languageo"),
        ("Titleo"),
        ("Creatoro"),
        ("Publishero"),
        ("Dateo"),
        ("Illustration_48x48@1o"),
        ("Illustration_96x96@1o"),
        ("Descriptiono"),
        ("LongDescriptiono"),
        ("Tagso"),
        ("Scrapero"),
        ("Flavouro"),
        ("Sourceo"),
        ("Licenseo"),
        ("Relationo"),
        ("Countero"),
    ],
)
@pytest.mark.parametrize(
    "metadata_type",
    [
        (metadata.CustomMetadata),
        (metadata.CustomTextMetadata),
    ],
)
def test_nonreserved_custom(metadata_name: str, metadata_type: type):
    value = "x" if metadata_type == metadata.CustomTextMetadata else b"x"
    assert metadata_type(name=metadata_name, value=value)


def test_mandatory_value(metadata_init: MetadataInitConfig):
    if not getattr(metadata_init.a_type, "is_required", False):
        pytest.skip("Only testing mandatory ones")
    with pytest.raises(ValueError, match="Missing"):
        if issubclass(metadata_init.a_type, metadata.TextListBasedMetadata):
            metadata_init.a_type([])
            metadata_init.a_type(["", " "])
        elif issubclass(metadata_init.a_type, metadata.TextBasedMetadata):
            metadata_init.a_type("")
            metadata_init.a_type(" ")
        elif issubclass(metadata_init.a_type, metadata.DateBasedMetadata):
            pytest.skip("Cannot set an empty Date")
        elif issubclass(metadata_init.a_type, metadata.DefaultIllustrationMetadata):
            metadata_init.a_type(b"")  # pyright:ignore[reportUnknownMemberType]
            metadata_init.a_type(b" ")  # pyright:ignore[reportUnknownMemberType]
        elif get_classvar_value_type(metadata_init.a_type) is bytes:
            if metadata_init.nb_args == 1:
                metadata_init.a_type(b"")  # pyright: ignore[reportCallIssue]
                metadata_init.a_type(b" ")  # pyright: ignore[reportCallIssue]
            else:
                metadata_init.a_type(
                    b"", name="Foo"  # pyright: ignore[reportCallIssue]
                )
                metadata_init.a_type(
                    b" ", name="Foo"  # pyright: ignore[reportCallIssue]
                )
        else:
            raise OSError("WTF")


def test_clean_value(metadata_init: MetadataInitConfig):
    raw_value = "\t\n\r\n \tA val \t\awith  \bcontrol chars\v\n"
    clean_value = b"A val \twith  control chars"
    raw_lang_value = "\t\n\r\n \tfra \t\a\b\v\n"
    clean_lang_value = b"fra"
    if metadata_init.a_type == metadata.LanguageMetadata:
        assert metadata_init.a_type([raw_lang_value]).libzim_value == clean_lang_value
    elif isinstance(metadata_init.a_type, metadata.TextListBasedMetadata):
        assert metadata_init.a_type(raw_value).libzim_value == clean_value
        assert metadata_init.a_type(
            value=[raw_value, raw_value]
        ).libzim_value == metadata_init.a_type.join_list_with.join(
            [clean_value.decode("UTF-8")]
        ).encode(
            "UTF-8"
        )
    elif isinstance(metadata_init.a_type, metadata.TextBasedMetadata):
        if metadata_init.nb_args == 1:
            assert metadata_init.a_type(value=raw_value).libzim_value == clean_value
        else:
            assert (
                metadata_init.a_type(value=raw_value, name="Foo").libzim_value
                == clean_value
            )


def test_libzim_bytes_value(metadata_init: MetadataInitConfig, png_image: pathlib.Path):
    if metadata_init.nb_args == 2:
        if metadata_init.a_type == metadata.IllustrationMetadata:
            with open(png_image, "rb") as fh:
                png_data = fh.read()
            assert metadata_init.a_type(png_data, 48).libzim_value == png_data
        elif metadata_init.a_type in (
            metadata.CustomTextMetadata,
            metadata.XCustomTextMetadata,
        ):
            assert (
                metadata_init.a_type(value="a value", name="Foo").libzim_value
                == b"a value"
            )
        elif metadata_init.a_type in (
            metadata.CustomMetadata,
            metadata.XCustomMetadata,
        ):
            assert (
                metadata_init.a_type(value=b"a value", name="Foo").libzim_value
                == b"a value"
            )
        else:
            assert (
                metadata_init.a_type(value=b"a value", name="Foo").libzim_value
                == b"a value"
            )
    elif metadata_init.nb_args == 1:
        if metadata_init.a_type == metadata.DefaultIllustrationMetadata:
            with open(png_image, "rb") as fh:
                png_data = fh.read()
            assert metadata_init.a_type(png_data).libzim_value == png_data
        elif metadata_init.a_type == metadata.DateMetadata:
            assert (
                metadata_init.a_type(datetime.date(2023, 12, 11)).libzim_value
                == b"2023-12-11"
            )
        elif metadata_init.a_type == metadata.LanguageMetadata:
            assert metadata_init.a_type(["fra", "eng"]).libzim_value == b"fra,eng"
        else:
            assert metadata_init.a_type("a value").libzim_value == b"a value"


def test_libzim_io_bytesio_value(
    metadata_init: MetadataInitConfig, png_image: pathlib.Path
):
    if metadata_init.a_type == metadata.DefaultIllustrationMetadata:
        with open(png_image, "rb") as fh:
            png_data = fh.read()
        assert metadata_init.a_type(value=io.BytesIO(png_data)).libzim_value == png_data
    elif metadata_init.a_type == metadata.IllustrationMetadata:
        with open(png_image, "rb") as fh:
            png_data = fh.read()
        assert (
            metadata_init.a_type(value=io.BytesIO(png_data), size=48).libzim_value
            == png_data
        )
    elif get_classvar_value_type(metadata_init.a_type) in (
        bytes,
        BinaryIO,
        io.BytesIO,
    ):
        if metadata_init.nb_args == 1:
            assert (
                metadata_init.a_type(value=io.BytesIO(b"a value")).libzim_value
                == b"a value"
            )
        else:
            assert (
                metadata_init.a_type(
                    value=io.BytesIO(b"a value"), name="Foo"
                ).libzim_value
                == b"a value"
            )
    else:
        pytest.skip("Type doesnt support bytes-like input")


def test_std_metadata_values():
    test_value = dataclasses.replace(metadata.DEFAULT_DEV_ZIM_METADATA)
    test_value.License = metadata.LicenseMetadata("Creative Commons CC0")
    values = test_value.values()
    assert len(values) == 9

    expected_values: list[metadata.AnyMetadata] = [
        metadata.LicenseMetadata("Creative Commons CC0"),
        metadata.NameMetadata("Test Name"),
        metadata.TitleMetadata("Test Title"),
        metadata.CreatorMetadata("Test Creator"),
        metadata.PublisherMetadata("Test Publisher"),
        metadata.DateMetadata(datetime.date(2023, 1, 1)),
        metadata.DescriptionMetadata("Test Description"),
        metadata.LanguageMetadata("fra"),
        # blank 48x48 transparent PNG
        metadata.DefaultIllustrationMetadata(
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


def test_raw_metadata():
    assert metadata.Metadata(name="Name", value=b"hello")


def test_decorators():
    @metadata.allow_empty
    class MyMetadata(metadata.XCustomTextMetadata): ...

    assert MyMetadata("Test", "value").libzim_value == b"value"

    @metadata.allow_duplicates
    class MyMetadata2(metadata.TextListBasedMetadata):
        join_list_with = "|"

    assert (
        MyMetadata2(name="Test", value=["value", "hello", "value"]).libzim_value
        == b"value|hello|value"
    )

    raw_value = "\t\n\r\n \tA val \t\awith  \bcontrol chars\v\n"

    class MyMetadata3(metadata.TextBasedMetadata):
        require_text_cleanup = False

    assert MyMetadata3(name="Test", value=raw_value).libzim_value == raw_value.encode(
        "UTF-8"
    )

    @metadata.allow_duplicates
    class MyMetadata4(metadata.TextListBasedMetadata):
        require_textlist_cleanup = False
        join_list_with = "|"

    assert MyMetadata4(
        name="Test", value=(raw_value, raw_value)
    ).libzim_value == "|".join([raw_value, raw_value]).encode("UTF-8")


def test_custom_ones():
    textval = "value"
    value = textval.encode("UTF-8")
    assert metadata.CustomMetadata("Test", value).libzim_value == value
    assert metadata.XCustomMetadata("Name", value).libzim_value == value
    assert metadata.XCustomMetadata("Name", value).name == "X-Name"
    assert metadata.CustomTextMetadata("Test", textval).libzim_value == value
    assert metadata.XCustomTextMetadata("Name", textval).libzim_value == value
    assert metadata.XCustomTextMetadata("Name", textval).name == "X-Name"
    with pytest.raises(ValueError, match="must be X- prefixed"):
        metadata.CustomMetadata("Name", value)
    with pytest.raises(ValueError, match="must be X- prefixed"):
        metadata.CustomTextMetadata("Name", textval)


def test_mandatory_zim_metadata_keys():
    # as per the spec on 2024-12-13
    assert len(metadata.MANDATORY_ZIM_METADATA_KEYS) >= 8
    assert "Illustration_48x48@1" in metadata.MANDATORY_ZIM_METADATA_KEYS


def test_default_dev_zim_metadata():
    assert isinstance(metadata.DEFAULT_DEV_ZIM_METADATA, metadata.StandardMetadataList)
    # as per the spec on 2024-12-13
    assert len(metadata.DEFAULT_DEV_ZIM_METADATA.values()) == 8


def test_get_binary_from(png_image: pathlib.Path):
    with open(png_image, "rb") as fh:
        png_data = fh.read()
    # bytes input
    assert metadata.Metadata(value=png_data, name="Test").libzim_value == png_data
    # io.BytesIO input
    assert (
        metadata.Metadata(value=io.BytesIO(png_data), name="Test").libzim_value
        == png_data
    )
    # BaseIO input
    with open(png_image, "rb") as fh:
        assert metadata.Metadata(value=fh, name="Test").libzim_value == png_data

    # unseekbale BaseIO
    def notseekable():
        return False

    with open(png_image, "rb") as fh:
        fh.seekable = notseekable
        assert metadata.Metadata(value=fh, name="Test").libzim_value == png_data


def test_ensure_missingname_raises():
    with pytest.raises(OSError, match="name missing"):
        metadata.Metadata(b"yello")


def test_mimetype_usage():
    mimetype = "video/webm"
    assert metadata.Metadata(b"hello", "Test", mimetype=mimetype).mimetype == mimetype
    assert metadata.Metadata(b"hello", "Test").mimetype == "text/plain;charset=UTF-8"
    assert (
        metadata.DEFAULT_DEV_ZIM_METADATA.Illustration_48x48_at_1.mimetype
        == "image/png"
    )
