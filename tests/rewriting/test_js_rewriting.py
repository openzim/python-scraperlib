from collections.abc import Callable

import pytest

from zimscraperlib.rewriting.js import JsRewriter
from zimscraperlib.rewriting.url_rewriting import (
    ArticleUrlRewriter,
    HttpUrl,
    ZimPath,
)

from .utils import ContentForTests


@pytest.fixture
def simple_js_rewriter(
    simple_url_rewriter_gen: Callable[[str], ArticleUrlRewriter]
) -> JsRewriter:
    return JsRewriter(
        url_rewriter=simple_url_rewriter_gen("http://www.example.com"),
        base_href=None,
        notify_js_module=None,
    )


@pytest.fixture(
    params=[
        "a = this;",
        "return this.location",
        'func(Function("return this"));',
        "'a||this||that",
        "(a,b,Q.contains(i[t], this))",
        "a = this.location.href; exports.Foo = Foo; /* export className */",
    ]
)
def rewrite_this_js_content(request: pytest.FixtureRequest):
    content = request.param
    yield ContentForTests(
        input_=content,
        expected=content.replace(
            "this", "_____WB$wombat$check$this$function_____(this)"
        ),
    )


def test_this_js_rewrite(
    simple_js_rewriter: JsRewriter, rewrite_this_js_content: ContentForTests
):
    assert (
        simple_js_rewriter.rewrite(rewrite_this_js_content.input_str)
        == rewrite_this_js_content.expected_str
    )


@pytest.fixture(
    params=[
        "aaa.this.window=red",
        "aaa. this.window=red",
        "aaa$this.window=red",
        "a = this.color;",
        "return this.color",
        'func(Function("return this.color"));',
        "'a||this.color||that",
        "(a,b,Q.contains(i[t], this.color))",
        "a = this.color.href; exports.Foo = Foo; /* export className */",
    ]
)
def no_rewrite_this_js_content(request: pytest.FixtureRequest):
    content = request.param
    yield ContentForTests(input_=content)


def test_this_no_js_rewrite(
    simple_js_rewriter: JsRewriter, no_rewrite_this_js_content: ContentForTests
):
    assert (
        simple_js_rewriter.rewrite(no_rewrite_this_js_content.input_str)
        == no_rewrite_this_js_content.expected_str
    )


# This test probably has to be fixed but spec is blurry
# See https://github.com/openzim/warc2zim/issues/410
def test_this_js_rewrite_newline(simple_js_rewriter: JsRewriter):
    assert (
        simple_js_rewriter.rewrite("aaa\n  this.window=red")
        == "aaa\n  ;_____WB$wombat$check$this$function_____(this).window=red"
    )


def test_js_rewrite_bytes_inline(simple_js_rewriter: JsRewriter):
    assert (
        simple_js_rewriter.rewrite(b"a=123;\nb=456;", opts={"inline": True})
        == "a=123; b=456;"
    )


def test_js_rewrite_post_message(simple_js_rewriter: JsRewriter):
    assert (
        simple_js_rewriter.rewrite(b"a.postMessage(") == "a.__WB_pmw(self).postMessage("
    )


class WrappedTestContent(ContentForTests):

    def __init__(
        self,
        input_: str | bytes,
        expected: str | bytes | None = None,
        article_url: str = "https://kiwix.org",
    ) -> None:
        super().__init__(input_=input_, expected=expected, article_url=article_url)
        self.expected = self.wrap_script(self.expected_str)

    @staticmethod
    def wrap_script(text: str) -> str:
        """
        A small wrapper to help generate the expected content.

        JsRewriter must add this local definition around all js code (when we access on
        of the local varibles)
        """
        return (
            "var _____WB$wombat$assign$function_____ = function(name) {return (self."
            "_wb_wombat && self._wb_wombat.local_init && self._wb_wombat.local_init"
            "(name)) || self[name]; };\n"
            "if (!self.__WB_pmw) { self.__WB_pmw = function(obj) { this.__WB_source ="
            " obj; return this; } }\n"
            "{\n"
            'let window = _____WB$wombat$assign$function_____("window");\n'
            'let globalThis = _____WB$wombat$assign$function_____("globalThis");\n'
            'let self = _____WB$wombat$assign$function_____("self");\n'
            'let document = _____WB$wombat$assign$function_____("document");\n'
            'let location = _____WB$wombat$assign$function_____("location");\n'
            'let top = _____WB$wombat$assign$function_____("top");\n'
            'let parent = _____WB$wombat$assign$function_____("parent");\n'
            'let frames = _____WB$wombat$assign$function_____("frames");\n'
            'let opener = _____WB$wombat$assign$function_____("opener");\n'
            "let arguments;\n"
            "\n"
            f"{text}"
            "\n"
            "}"
        )


@pytest.fixture(
    params=[
        WrappedTestContent(
            input_="location = http://example.com/",
            expected="location = ((self.__WB_check_loc && "
            "self.__WB_check_loc(location, argument"
            "s)) || {}).href = http://example.com/",
        ),
        WrappedTestContent(
            input_=" location = http://example.com/2",
            expected=" location = ((self.__WB_check_loc && "
            "self.__WB_check_loc(location, arguments)) || {}).href = "
            "http://example.com/2",
        ),
        WrappedTestContent(input_="func(location = 0)", expected="func(location = 0)"),
        WrappedTestContent(
            input_=" location = http://example.com/2",
            expected=" location = ((self.__WB_check_loc && "
            "self.__WB_check_loc(location, arguments)) || {}).href = "
            "http://example.com/2",
        ),
        WrappedTestContent(input_="window.eval(a)", expected="window.eval(a)"),
        WrappedTestContent(
            input_="x = window.eval; x(a);", expected="x = window.eval; x(a);"
        ),
        WrappedTestContent(
            input_="this. location = 'http://example.com/'",
            expected="this. location = 'http://example.com/'",
        ),
        WrappedTestContent(
            input_="if (self.foo) { console.log('blah') }",
            expected="if (self.foo) { console.log('blah') }",
        ),
        WrappedTestContent(input_="window.x = 5", expected="window.x = 5"),
    ]
)
def rewrite_wrapped_content(request: pytest.FixtureRequest):
    yield request.param


def test_wrapped_rewrite(
    simple_js_rewriter: JsRewriter, rewrite_wrapped_content: WrappedTestContent
):
    assert (
        simple_js_rewriter.rewrite(rewrite_wrapped_content.input_str)
        == rewrite_wrapped_content.expected_str
    )


class ImportTestContent(ContentForTests):

    def __init__(
        self,
        input_: str | bytes,
        expected: str | bytes | None = None,
        article_url: str = "https://kiwix.org",
    ) -> None:
        super().__init__(input_=input_, expected=expected, article_url=article_url)
        self.article_url = "https://exemple.com/some/path/"
        self.expected = self.wrap_import(self.expected_str)

    @staticmethod
    # We want to import js stored in zim file as `_zim_static/__wb_module_decl.js` from
    # `https://exemple.com/some/path/` so path is
    # `../../../_zim_static/__wb_module_decl.js`
    def wrap_import(text: str) -> str:
        """
        A small wrapper to help us generate the expected content for modules.

        JsRewriter must add this import line at beginning of module codes (when code
        contains `import` or `export`)
        """
        return (
            "import { window, globalThis, self, document, location, top, parent, "
            'frames, opener } from "../../../_zim_static/__wb_module_decl.js";\n'
            f"{text}"
        )


@pytest.fixture(
    params=[
        # import rewrite
        ImportTestContent(
            input_="""import "foo";

a = this.location""",
            expected="""import "foo";

a = _____WB$wombat$check$this$function_____(this).location""",
        ),
        # import/export module rewrite
        ImportTestContent(
            input_="""a = this.location

export { a };
""",
            expected="""a = _____WB$wombat$check$this$function_____(this).location

export { a };
""",
        ),
        # rewrite ESM module import
        ImportTestContent(
            input_='import "https://example.com/file.js"',
            expected='import "../../../example.com/file.js"',
        ),
        ImportTestContent(
            input_='''
import {A, B}
 from
 "https://example.com/file.js"''',
            expected='''
import {A, B}
 from
 "../../../example.com/file.js"''',
        ),
        ImportTestContent(
            input_="""
import * from "https://example.com/file.js"
import A from "http://example.com/path/file2.js";

import {C, D} from "./abc.js";
import {X, Y} from "../parent.js";
import {E, F, G} from "/path.js";
import { Z } from "../../../path.js";

B = await import(somefile);
""",
            expected="""
import * from "../../../example.com/file.js"
import A from "../../../example.com/path/file2.js";

import {C, D} from "./abc.js";
import {X, Y} from "../parent.js";
import {E, F, G} from "../../path.js";
import { Z } from "../../path.js";

B = await ____wb_rewrite_import__(import.meta.url, somefile);
""",
        ),
        ImportTestContent(
            input_='import"import.js";import{A, B, C} from"test.js";(function() => '
            '{ frames[0].href = "/abc"; })',
            expected='import"import.js";import{A, B, C} from"test.js";(function() => '
            '{ frames[0].href = "/abc"; })',
        ),
        ImportTestContent(
            input_="""a = location

export{ a, $ as b};
""",
            expected="""a = location

export{ a, $ as b};
""",
        ),
    ]
)
def rewrite_import_content(request: pytest.FixtureRequest):
    yield request.param


def test_import_rewrite(rewrite_import_content: ImportTestContent):
    url_rewriter = ArticleUrlRewriter(
        article_url=HttpUrl(rewrite_import_content.article_url)
    )
    assert (
        JsRewriter(
            url_rewriter=url_rewriter, base_href=None, notify_js_module=None
        ).rewrite(rewrite_import_content.input_str, opts={"isModule": True})
        == rewrite_import_content.expected_str
    )


@pytest.fixture(
    params=[
        "return this.abc",
        "return this object",
        "a = 'some, this object'",
        "{foo: bar, this: other}",
        "this.$location = http://example.com/",
        "this.  $location = http://example.com/",
        "this. _location = http://example.com/",
        "this. alocation = http://example.com/",
        "this.location = http://example.com/",
        ",eval(a)",
        "this.$eval(a)",
        "x = $eval; x(a);",
        "obj = { eval : 1 }",
        "x = obj.eval",
        "x = obj.eval(a)",
        "x = obj._eval(a)",
        "x = obj.$eval(a)",
        "if (a.self.foo) { console.log('blah') }",
        "a.window.x = 5",
        "  postMessage({'a': 'b'})",
        "simport(5);",
        "a.import(5);",
        "$import(5);",
        "async import(val) { ... }",
        """function blah() {
  const text = "text: import a from B.js";
}
""",
        """function blah() {
  const text = `
import a from "https://example.com/B.js"
`;
}

""",
        "let a = 7; var b = 5; const foo = 4;\n\n",
    ]
)
def no_rewrite_js_content(request: pytest.FixtureRequest):
    yield request.param


def test_no_rewrite(simple_js_rewriter: JsRewriter, no_rewrite_js_content: str):
    assert simple_js_rewriter.rewrite(no_rewrite_js_content) == no_rewrite_js_content


@pytest.mark.parametrize(
    "js_src,expected_js_module_path",
    [
        ("./my-module-script.js", "kiwix.org/my_folder/my-module-script.js"),
        ("../my-module-script.js", "kiwix.org/my-module-script.js"),
        ("../../../my-module-script.js", "kiwix.org/my-module-script.js"),
        ("/my-module-script.js", "kiwix.org/my-module-script.js"),
        ("//myserver.com/my-module-script.js", "myserver.com/my-module-script.js"),
        (
            "https://myserver.com/my-module-script.js",
            "myserver.com/my-module-script.js",
        ),
    ],
)
def test_js_rewrite_nested_module_detected(js_src: str, expected_js_module_path: str):

    js_modules: list[ZimPath] = []

    def custom_notify(zim_path: ZimPath):
        js_modules.append(zim_path)

    url_rewriter = ArticleUrlRewriter(
        article_url=HttpUrl("http://kiwix.org/my_folder/my_article.html")
    )

    JsRewriter(
        url_rewriter=url_rewriter, base_href=None, notify_js_module=custom_notify
    ).rewrite(f'import * from "{js_src}"', opts={"isModule": True})

    assert len(js_modules) == 1
    assert js_modules[0].value == expected_js_module_path
