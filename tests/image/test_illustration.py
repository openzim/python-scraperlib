from pathlib import Path

import pytest
from PIL.Image import open as pilopen

from zimscraperlib.image.illustration import get_zim_illustration

COMMONS_IMAGE_PATH = (Path(__file__) / "../../files/commons.png").resolve()
COMMONS_48_IMAGE_PATH = (Path(__file__) / "../../files/commons48.png").resolve()
NINJA_IMAGE_PATH = (Path(__file__) / "../../files/ninja.webp").resolve()


@pytest.mark.parametrize(
    "user_illustration, expected_max_filesize",
    [
        pytest.param(COMMONS_IMAGE_PATH, 5000, id="big_commons"),
        pytest.param(COMMONS_48_IMAGE_PATH, 4000, id="small_commons"),
        pytest.param(NINJA_IMAGE_PATH, 5000, id="ninja"),
        pytest.param(
            "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4a/Commons-logo.svg/250px-Commons-logo.svg.png",
            4000,
            id="png_url",
        ),
        pytest.param(
            "https://upload.wikimedia.org/wikipedia/commons/4/4a/Commons-logo.svg",
            4000,
            id="svg_url",
        ),
    ],
)
def test_get_zim_illustration(
    user_illustration: str | Path,
    expected_max_filesize: int,
):
    image = get_zim_illustration(user_illustration)
    assert len(image.getvalue()) < expected_max_filesize
    with pilopen(image) as image_details:
        assert image_details.format == "PNG"
        assert image_details.size == (48, 48)


def test_get_missing_user_zim_illustration():
    with pytest.raises(Exception, match=r"missing\.png could not be found"):
        get_zim_illustration("./missing.png")


def test_get_missing_default_zim_illustration():
    with pytest.raises(Exception, match="Illustration is missing"):
        get_zim_illustration("")


def test_get_zim_illustration_custom_size():
    image = get_zim_illustration(NINJA_IMAGE_PATH, 96, 120)
    assert len(image.getvalue()) < 21000
    with pilopen(image) as image_details:
        assert image_details.format == "PNG"
        assert image_details.size == (96, 120)


def test_get_zim_illustration_method():
    image_cover = get_zim_illustration(NINJA_IMAGE_PATH, resize_method="cover")
    image_contain = get_zim_illustration(NINJA_IMAGE_PATH, resize_method="contain")
    # cover image is always bigger than contain image size more pixels are
    # "used/non-transparent"
    assert len(image_cover.getvalue()) > len(image_contain.getvalue())
    for image in [image_cover, image_contain]:
        with pilopen(image) as image_details:
            assert image_details.format == "PNG"
            assert image_details.size == (48, 48)
