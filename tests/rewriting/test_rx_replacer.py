import re
from collections.abc import Callable

import pytest

from zimscraperlib.rewriting.rx_replacer import (
    RxRewriter,
    TransformationAction,
    add_prefix,
    add_suffix,
    replace,
    replace_all,
    replace_prefix_from,
)


@pytest.fixture()
def compiled_rule() -> re.Pattern[str]:
    return re.compile("<replaced>")


@pytest.mark.parametrize(
    "operation, operand1, expected_result",
    [
        (add_suffix, "456", "pre<replaced>456post"),
        (add_prefix, "456", "pre456<replaced>post"),
        (replace_all, "456", "pre456post"),
    ],
)
def test_actions_one(
    compiled_rule: re.Pattern[str],
    operation: Callable[[str], TransformationAction],
    operand1: str,
    expected_result: str,
):
    def wrapped(operation: Callable[[str], TransformationAction], operand1: str):
        def wraper(match: re.Match[str]):
            return operation(operand1)(match, {})

        return wraper

    assert (
        compiled_rule.sub(wrapped(operation, operand1), "pre<replaced>post")
        == expected_result
    )


@pytest.mark.parametrize(
    "operation, operand1, operand2, expected_result",
    [
        (replace_prefix_from, "456", "pl", "pre<re456post"),
        (replace_prefix_from, "456", "<repl", "pre456post"),
        (replace, "epla", "456", "pre<r456ced>post"),
    ],
)
def test_actions_two(
    compiled_rule: re.Pattern[str],
    operation: Callable[[str, str], TransformationAction],
    operand1: str,
    operand2: str,
    expected_result: str,
):
    def wrapped(
        operation: Callable[[str, str], TransformationAction],
        operand1: str,
        operand2: str,
    ):
        def wraper(match: re.Match[str]):
            return operation(operand1, operand2)(match, {})

        return wraper

    assert (
        compiled_rule.sub(wrapped(operation, operand1, operand2), "pre<replaced>post")
        == expected_result
    )


@pytest.mark.parametrize(
    "text, expected",
    [
        ("pre<replaced>post", "pre<re123ced>post"),
        (b"pre<replaced>post", "pre<re123ced>post"),
        ("foo", "f456"),
        ("bar", "bar"),
        ("blu", "blu"),
    ],
)
def test_rx_rewriter(text: str, expected: str):
    rewriter = RxRewriter(
        rules=[
            (re.compile("foo"), replace("oo", "456")),
            (re.compile("bar"), replace("oo", "456")),
            (re.compile("<replaced>"), replace("pla", "123")),
        ]
    )
    assert rewriter.rewrite(text) == expected


def test_rx_rewriter_no_rules():
    rewriter = RxRewriter()
    rewriter._compile_rules(  # pyright: ignore[reportPrivateUsage]
        [
            (re.compile("<replaced>"), replace("pla", "123")),
        ]
    )
    assert rewriter.rewrite("pre<replaced>post") == "pre<re123ced>post"
