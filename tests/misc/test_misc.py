import pytest

from zimscraperlib.misc import first


@pytest.mark.parametrize(
    "args,expected",
    [
        (["", None, "a"], ""),
        ([None, None], ""),
        ([None], ""),
        ([None, None, "a", None, "b"], "a"),
    ],
)
def test_first(args, expected):
    assert first(*args) == expected
