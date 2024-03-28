#!/usr/bin/env python3
# vim: ai ts=4 sts=4 et sw=4 nu

from __future__ import annotations

import pathlib

import pytest

import zimscraperlib
from zimscraperlib.constants import CONTACT
from zimscraperlib.constants import (
    MAXIMUM_DESCRIPTION_METADATA_LENGTH as MAX_DESC_LENGTH,
)
from zimscraperlib.constants import (
    MAXIMUM_LONG_DESCRIPTION_METADATA_LENGTH as MAX_LONG_DESC_LENGTH,
)
from zimscraperlib.constants import NAME as PROJECT_NAME
from zimscraperlib.inputs import compute_descriptions, handle_user_provided_file


def test_with_none():
    assert handle_user_provided_file(source=None) is None


def test_empty_value():
    assert handle_user_provided_file(source=" ") is None


def test_missing_local():
    with pytest.raises(IOError):
        handle_user_provided_file(source="/some/incorrect/path.txt")


def test_local_copy(png_image):
    fpath = handle_user_provided_file(source=str(png_image))
    assert fpath is not None
    assert fpath.exists()
    assert fpath.suffix == png_image.suffix
    assert fpath.stat().st_size == png_image.stat().st_size


def test_local_nocopy(png_image):
    fpath = handle_user_provided_file(source=str(png_image), nocopy=True)
    assert fpath is not None
    assert fpath.exists()
    assert str(fpath) == str(png_image)


def test_remote(valid_http_url):
    fpath = handle_user_provided_file(source=valid_http_url)
    assert fpath is not None
    assert fpath.exists()
    assert fpath.suffix == pathlib.Path(valid_http_url).suffix


def test_local_dest(tmp_path, png_image):
    dest = tmp_path / png_image.name
    fpath = handle_user_provided_file(source=str(png_image), dest=dest)
    assert fpath is not None
    assert fpath.exists()
    assert fpath == dest


def test_remote_dest(tmp_path, valid_http_url):
    dest = tmp_path / pathlib.Path(valid_http_url).name
    fpath = handle_user_provided_file(source=valid_http_url, dest=dest)
    assert fpath is not None
    assert fpath.exists()
    assert fpath == dest


def test_local_indir(tmp_path, png_image):
    fpath = handle_user_provided_file(source=str(png_image), in_dir=tmp_path)
    assert fpath is not None
    assert fpath.exists()
    assert fpath.parent == tmp_path


def test_remote_indir(tmp_path, valid_http_url):
    fpath = handle_user_provided_file(source=valid_http_url, in_dir=tmp_path)
    assert fpath is not None
    assert fpath.exists()
    assert fpath.parent == tmp_path


def test_remote_default_user_agent(valid_http_url, monkeypatch):
    def mock_stream_file(**kwargs):
        headers = kwargs.get("headers")
        assert headers is not None
        user_agent = headers.get("User-Agent")
        assert isinstance(user_agent, str)
        assert user_agent.startswith(f"{PROJECT_NAME}/")
        assert user_agent.endswith(f"({CONTACT})")

    monkeypatch.setattr(
        zimscraperlib.inputs,  # pyright: ignore[reportAttributeAccessIssue]
        "stream_file",
        mock_stream_file,
        raising=True,
    )
    handle_user_provided_file(source=valid_http_url)


def test_remote_provided_user_agent(valid_http_url, valid_user_agent, monkeypatch):
    def mock_stream_file(**kwargs):
        headers = kwargs.get("headers")
        assert headers is not None
        user_agent = headers.get("User-Agent")
        assert isinstance(user_agent, str)
        assert user_agent == valid_user_agent

    monkeypatch.setattr(
        zimscraperlib.inputs,  # pyright: ignore[reportAttributeAccessIssue]
        "stream_file",
        mock_stream_file,
        raising=True,
    )
    handle_user_provided_file(source=valid_http_url, user_agent=valid_user_agent)


def test_remote_provided_none_user_agent(valid_http_url, monkeypatch):
    def mock_stream_file(**kwargs):
        assert kwargs.get("headers") is None

    monkeypatch.setattr(
        zimscraperlib.inputs,  # pyright: ignore[reportAttributeAccessIssue]
        "stream_file",
        mock_stream_file,
        raising=True,
    )
    handle_user_provided_file(source=valid_http_url, user_agent=None)


TEXT_NOT_USED = "text not used"

LONG_TEXT = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor "
    "incididunt ut labore et dolore magna aliqua. At erat pellentesque adipiscing "
    "commodo elit at imperdiet. Rutrum tellus pellentesque eu tincidunt tortor aliquam"
    " nulla facilisi. Eget lorem dolor sed viverra ipsum nunc. Ipsum nunc aliquet "
    "bibendum enim facilisis gravida neque convallis. Aliquam malesuada bibendum arcu "
    "vitae elementum curabitur. Platea dictumst quisque sagittis purus sit amet "
    "volutpat. Blandit libero volutpat sed cras ornare. In eu mi bibendum neque "
    "egestas. Egestas dui id ornare arcu odio. Pulvinar neque laoreet suspendisse "
    "interdum. Fames ac turpis egestas integer eget aliquet nibh praesent tristique. Et"
    " egestas quis ipsum suspendisse ultrices gravida dictum fusce. Malesuada fames ac "
    "turpis egestas. Tincidunt nunc pulvinar sapien et ligula ullamcorper malesuada "
    "proin libero. In arcu cursus euismod quis viverra. Faucibus in ornare quam viverra"
    ". Curabitur vitae nunc sed velit dignissim sodales ut eu sem. Velit scelerisque in"
    " dictum non consectetur a erat nam. Proin fermentum leo vel orci porta non. Fames"
    " ac turpis egestas sed tempus. Vitae justo eget magna fermentum iaculis eu non. "
    "Imperdiet massa tincidunt nunc pulvinar sapien et ligula. Laoreet sit amet cursus "
    "sit amet dictum sit amet. Quis hendrerit dolor magna eget. Orci ac auctor augue "
    "mauris augue. Consequat interdum varius sit amet mattis. At ultrices mi tempus "
    "imperdiet nulla malesuada pellentesque elit. Volutpat est velit egestas dui. "
    "Potenti nullam ac tortor vitae. At tempor commodo ullamcorper a lacus vestibulum "
    "sed arcu non. Duis ut diam quam nulla. Vestibulum mattis ullamcorper velit sed "
    "ullamcorper. Sit amet commodo nulla facilisi nullam vehicula. Faucibus purus in "
    "massa tempor nec feugiat. Sem fringilla ut morbi tincidunt augue interdum velit. "
    "Etiam dignissim diam quis enim lobortis scelerisque fermentum dui. Nunc vel risus "
    "commodo viverra maecenas accumsan. Aenean sed adipiscing diam donec adipiscing "
    "tristique. Maecenas accumsan lacus vel facilisis volutpat est velit egestas. Nulla"
    " aliquet porttitor lacus luctus accumsan tortor posuere ac. Habitant morbi "
    "tristique senectus et netus et. Eget mi proin sed libero enim sed faucibus turpis "
    "in. Vulputate enim nulla aliquet porttitor lacus. Dui ut ornare lectus sit amet "
    "est. Quam lacus suspendisse faucibus interdum posuere. Sagittis orci a scelerisque"
    " purus semper eget duis at tellus. Tellus molestie nunc non blandit massa. Feugiat"
    " vivamus at augue eget arcu dictum varius duis at. Varius morbi enim nunc faucibus"
    " a pellentesque sit. Id aliquet lectus proin nibh nisl condimentum id venenatis a."
    " Tortor dignissim convallis aenean et tortor at risus viverra adipiscing. Aliquam "
    "malesuada bibendum arcu vitae elementum curabitur vitae nunc sed. Habitasse platea"
    " dictumst quisque sagittis purus sit amet volutpat. Vitae auctor eu augue ut "
    "lectus. At varius vel pharetra vel turpis nunc eget. Dictum at tempor  commodo "
    "ullamcorper a lacus vestibulum sed arcu. Pellentesque massa placerat duis "
    "ultricies. Enim nunc faucibus a pellentesque sit amet porttitor eget dolor. "
    "Volutpat blandit aliquam etiam erat velit scelerisque in. Amet mattis vulputate "
    "enim nulla aliquet porttitor. Egestas maecenas pharetra convallis posuere morbi "
    "leo urna molestie. Duis ut diam quam nulla porttitor massa id. In fermentum "
    "posuere urna nec tincidunt praesent. Turpis egestas sed tempus urna et pharetra "
    "pharetra massa. Tellus molestie nunc non blandit massa. Diam phasellus vestibulum "
    "lorem sed risus ultricies. Egestas erat imperdiet sed euismod nisi porta lorem. "
    "Quam viverra orci sagittis eu volutpat odio facilisis mauris sit. Ornare aenean "
    "euismod elementum nisi quis. Laoreet non curabitur gravida arcu ac tortor "
    "dignissim convallis aenean. Sagittis aliquam malesuada bibendum arcu vitae "
    "elementum. Sed blandit libero volutpat sed cras ornare. Sagittis eu volutpat odio "
    "facilisis mauris. Facilisis volutpat est velit egestas dui id ornare arcu odio. "
    "Eu feugiat pretium  nibh."
)


@pytest.mark.parametrize(
    "user_description, user_long_description, default_description, raises, "
    "expected_description, expected_long_description",
    [
        # user description set and is short, user long descripion not set, default
        # description doe not matter
        (
            LONG_TEXT[0:MAX_DESC_LENGTH],
            None,
            TEXT_NOT_USED,
            False,
            LONG_TEXT[0:MAX_DESC_LENGTH],
            None,
        ),
        # user description set and is too long, default description does not matter
        (LONG_TEXT[0 : MAX_DESC_LENGTH + 1], None, TEXT_NOT_USED, True, None, None),
        # user description not set and default description is short enough
        (
            None,
            None,
            LONG_TEXT[0:MAX_DESC_LENGTH],
            False,
            LONG_TEXT[0:MAX_DESC_LENGTH],
            None,
        ),
        # user description not set and default description is too long for description
        # but ok for long description
        (
            None,
            None,
            LONG_TEXT[0 : MAX_DESC_LENGTH + 1],
            False,
            LONG_TEXT[0 : MAX_DESC_LENGTH - 1] + "…",
            LONG_TEXT[0 : MAX_DESC_LENGTH + 1],
        ),
        (
            None,
            None,
            LONG_TEXT[0:MAX_LONG_DESC_LENGTH],
            False,
            LONG_TEXT[0 : MAX_DESC_LENGTH - 1] + "…",
            LONG_TEXT[0:MAX_LONG_DESC_LENGTH],
        ),
        # user description not set and default description is too long for description
        # and long description
        (
            None,
            None,
            LONG_TEXT[0 : MAX_LONG_DESC_LENGTH + 1],
            False,
            LONG_TEXT[0 : MAX_DESC_LENGTH - 1] + "…",
            LONG_TEXT[0 : MAX_LONG_DESC_LENGTH - 1] + "…",
        ),
        # user description set and is short, user long descripion set and is short,
        # default description does not matter
        (
            LONG_TEXT[0:MAX_DESC_LENGTH],
            LONG_TEXT[0:MAX_LONG_DESC_LENGTH],
            TEXT_NOT_USED,
            False,
            LONG_TEXT[0:MAX_DESC_LENGTH],
            LONG_TEXT[0:MAX_LONG_DESC_LENGTH],
        ),
        # user description set and is short, user long descripion set and is too long,
        # default description does not matter
        (
            LONG_TEXT[0:MAX_DESC_LENGTH],
            LONG_TEXT[0 : MAX_LONG_DESC_LENGTH + 1],
            TEXT_NOT_USED,
            True,
            None,
            None,
        ),
        # user description not set, user long descripion set and is short,
        # default description set to something different than long desc
        (
            None,
            LONG_TEXT[0:MAX_LONG_DESC_LENGTH],
            LONG_TEXT[10:MAX_LONG_DESC_LENGTH],
            False,
            LONG_TEXT[10 : MAX_DESC_LENGTH + 9] + "…",
            LONG_TEXT[0:MAX_LONG_DESC_LENGTH],
        ),
    ],
)
def test_description(
    user_description: str,
    user_long_description: str | None,
    default_description: str,
    *,
    raises: bool,
    expected_description: str,
    expected_long_description: str,
):
    if raises:
        with pytest.raises(ValueError):
            compute_descriptions(
                default_description, user_description, user_long_description
            )
        return
    else:
        (description, long_description) = compute_descriptions(
            default_description, user_description, user_long_description
        )

    assert description == expected_description
    assert long_description == expected_long_description
