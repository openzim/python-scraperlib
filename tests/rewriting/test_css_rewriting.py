from textwrap import dedent

import pytest

from zimscraperlib.rewriting.css import CssRewriter
from zimscraperlib.rewriting.url_rewriting import ArticleUrlRewriter, HttpUrl

from .utils import ContentForTests


@pytest.fixture(
    params=[
        ContentForTests(input_=b"p { color: red; }"),
        ContentForTests(input_=b"p {\n color: red;\n}"),
        ContentForTests(input_=b"p { background: blue; }"),
        ContentForTests(input_=b"p { background: rgb(15, 0, 52); }"),
        ContentForTests(
            input_=b"/* See bug issue at http://exemple.com/issue/link */ "
            b"p { color: blue; }"
        ),
        ContentForTests(
            input_=b"p { width= } div { background: url(http://exemple.com/img.png)}",
            expected=b"p { width= } div { background: url(../exemple.com/img.png)}",
        ),
        ContentForTests(
            input_=b"p { width= } div { background: url('http://exemple.com/img.png')}",
            expected=b'p { width= } div { background: url("../exemple.com/img.png")}',
        ),
        ContentForTests(
            input_=b'p { width= } div { background: url("http://exemple.com/img.png")}',
            expected=b'p { width= } div { background: url("../exemple.com/img.png")}',
        ),
    ]
)
def no_rewrite_content(request: pytest.FixtureRequest):
    yield request.param


def test_no_rewrite(no_rewrite_content: ContentForTests):
    assert (
        CssRewriter(
            ArticleUrlRewriter(
                article_url=HttpUrl(f"http://{no_rewrite_content.article_url}")
            ),
            base_href=None,
        ).rewrite(no_rewrite_content.input_bytes)
        == no_rewrite_content.expected_bytes.decode()
    )


def test_no_rewrite_str():
    test_css = "p {\n color: red;\n}"
    assert (
        CssRewriter(
            ArticleUrlRewriter(article_url=HttpUrl("http://kiwix.org")),
            base_href=None,
        ).rewrite(test_css)
        == test_css
    )


@pytest.fixture(
    params=[
        ContentForTests(input_='"border:'),
        ContentForTests(input_="border: solid 1px #c0c0c0; width= 100%"),
        # Despite being invalid, tinycss parse it as "width" property without value.
        ContentForTests(input_="width:", expected="width:;"),
        ContentForTests(
            input_="border-bottom-width: 1px;border-bottom-color: #c0c0c0;w"
        ),
        ContentForTests(
            input_='background: url("http://exemple.com/foo.png"); width=',
            expected='background: url("../exemple.com/foo.png"); width=',
        ),
    ]
)
def invalid_content_inline_with_fallback(request: pytest.FixtureRequest):
    yield request.param


def test_invalid_css_inline_with_fallback(
    invalid_content_inline_with_fallback: ContentForTests,
):
    assert (
        CssRewriter(
            ArticleUrlRewriter(
                article_url=HttpUrl(
                    f"http://{invalid_content_inline_with_fallback.article_url}"
                )
            ),
            base_href=None,
        ).rewrite_inline(invalid_content_inline_with_fallback.input_str)
        == invalid_content_inline_with_fallback.expected_str
    )


@pytest.fixture(
    params=[
        ContentForTests(input_='"border:', expected=""),
        ContentForTests(
            input_="border: solid 1px #c0c0c0; width= 100%",
            expected="border: solid 1px #c0c0c0; ",
        ),
        # Despite being invalid, tinycss parse it as "width" property without value.
        ContentForTests(input_="width:", expected="width:;"),
        ContentForTests(
            input_="border-bottom-width: 1px;border-bottom-color: #c0c0c0;w",
            expected="border-bottom-width: 1px;border-bottom-color: #c0c0c0;",
        ),
        ContentForTests(
            input_='background: url("http://exemple.com/foo.png"); width=',
            expected='background: url("../exemple.com/foo.png"); ',
        ),
    ]
)
def invalid_content_inline_no_fallback(request: pytest.FixtureRequest):
    yield request.param


def test_invalid_css_inline_no_fallback(
    invalid_content_inline_no_fallback: ContentForTests,
):
    assert (
        CssRewriter(
            ArticleUrlRewriter(
                article_url=HttpUrl(
                    f"http://{invalid_content_inline_no_fallback.article_url}"
                )
            ),
            base_href=None,
            remove_errors=True,
        ).rewrite_inline(invalid_content_inline_no_fallback.input_str)
        == invalid_content_inline_no_fallback.expected_str
    )


@pytest.fixture(
    params=[
        # Tinycss parse `"border:}` as a string with an unexpected eof in string.
        # At serialization, tiny try to recover and close the opened rule
        ContentForTests(input_=b'p {"border:}', expected=b'p {"border:}}'),
        ContentForTests(input_=b'"p {border:}'),
        ContentForTests(input_=b"p { border: solid 1px #c0c0c0; width= 100% }"),
        ContentForTests(input_=b"p { width: }"),
        ContentForTests(
            input_=b"p { border-bottom-width: 1px;border-bottom-color: #c0c0c0;w }"
        ),
        ContentForTests(
            input_=b'p { background: url("http://exemple.com/foo.png"); width= }',
            expected=b'p { background: url("../exemple.com/foo.png"); width= }',
        ),
    ]
)
def invalid_content(request: pytest.FixtureRequest):
    yield request.param


def test_invalid_cssl(invalid_content: ContentForTests):
    assert (
        CssRewriter(
            ArticleUrlRewriter(
                article_url=HttpUrl(f"http://{invalid_content.article_url}")
            ),
            base_href=None,
        ).rewrite(invalid_content.input_bytes)
        == invalid_content.expected_bytes.decode()
    )


def test_rewrite():
    content = b"""
/* A comment with a link : http://foo.com */
@import url(//fonts.googleapis.com/icon?family=Material+Icons);

p, input {
    color: rbg(1, 2, 3);
    background: url('http://kiwix.org/super/img');
    background-image:url('http://exemple.com/no_space_before_url');
}

@font-face {
    src: url(https://f.gst.com/s/qa/v31/6xKtdSZaE8KbpRA_hJFQNcOM.woff2) format('woff2');
}

@media only screen and (max-width: 40em) {
    p, input {
        background-image:url(data:image/png;base64,FooContent);
    }
}"""

    expected = """
    /* A comment with a link : http://foo.com */
    @import url(../fonts.googleapis.com/icon%3Ffamily%3DMaterial%20Icons);

    p, input {
        color: rbg(1, 2, 3);
        background: url("super/img");
        background-image:url("../exemple.com/no_space_before_url");
    }

    @font-face {
        src: url(../f.gst.com/s/qa/v31/6xKtdSZaE8KbpRA_hJFQNcOM.woff2) format("woff2");
    }

    @media only screen and (max-width: 40em) {
        p, input {
            background-image:url(data:image/png;base64,FooContent);
        }
    }"""
    expected = dedent(expected)

    assert (
        CssRewriter(
            ArticleUrlRewriter(article_url=HttpUrl("http://kiwix.org/article")),
            base_href=None,
        ).rewrite(content)
        == expected
    )
