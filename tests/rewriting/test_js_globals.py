"""Top-level declarations survive the wombat block (#329).

The rewriter wraps a script in `{ ... }` so wombat can shadow `window` and
friends. A block is a scope, so a `const`, `let` or `class` declared at the top
level of that script stops being visible to every other script on the page —
silently, because the script itself still runs.

These cases are ported from wabac.js's own suite (test/rewriteJS.ts), which is
the reference implementation this module tracks, with its expected strings kept
verbatim so a divergence shows up as a test failure rather than as a subtly
different ZIM.
"""

from collections.abc import Callable

import pytest

from zimscraperlib.rewriting.js import JsRewriter
from zimscraperlib.rewriting.js_ast import parser_available
from zimscraperlib.rewriting.url_rewriting import ArticleUrlRewriter

pytestmark = pytest.mark.skipif(
    not parser_available(), reason="no JavaScript parser installed"
)


@pytest.fixture
def js_rewriter(
    simple_url_rewriter_gen: Callable[[str], ArticleUrlRewriter],
) -> JsRewriter:
    return JsRewriter(
        url_rewriter=simple_url_rewriter_gen("http://www.example.com"),
        base_href=None,
        notify_js_module=None,
    )


def test_a_const_is_readable_after_the_block(js_rewriter: JsRewriter):
    # The bug that started #329: nerdfonts.com declares its glyph table as a
    # top-level const in one inline script and reads it from another.
    out = js_rewriter.rewrite("const glyphs = {a: 1};\nwindow.x = 1;")
    assert ";self.___WB_const_glyphs = glyphs;\n" in out
    assert (
        "const glyphs = self.___WB_const_glyphs; delete self.___WB_const_glyphs;" in out
    )
    assert out.index("self.___WB_const_glyphs = glyphs") < out.index("\n\n}")
    assert out.index("\n\n}") < out.index("const glyphs = self.___WB_const_glyphs")


def test_a_let_is_declared_before_the_block_and_assigned_inside(
    js_rewriter: JsRewriter,
):
    out = js_rewriter.rewrite("let counter = 4;\nwindow.x = 1;")
    assert out.startswith("let counter;\n")
    # The keyword is removed where it stood, so the assignment inside the block
    # writes the binding declared outside it.
    assert "\n counter = 4;" in out
    assert "let counter = 4" not in out


def test_a_class_travels_as_a_const(js_rewriter: JsRewriter):
    out = js_rewriter.rewrite("class Thing {}\nwindow.x = 1;")
    assert ";self.___WB_const_Thing = Thing;\n" in out
    assert "const Thing = self.___WB_const_Thing; delete self.___WB_const_Thing;" in out


def test_var_is_left_alone(js_rewriter: JsRewriter):
    # `var` is function-scoped, so the block never captured it and there is
    # nothing to carry.
    out = js_rewriter.rewrite("var legacy = 3;\nwindow.x = 1;")
    assert "___WB_const_legacy" not in out
    assert "var legacy = 3;" in out


def test_a_name_that_shadows_a_wombat_global_wins(js_rewriter: JsRewriter):
    # The script declares its own `location`; the wrapper must not declare one
    # too, or the script's declaration is a redeclaration in the same scope.
    out = js_rewriter.rewrite("const location = 'here';\nwindow.x = 1;")
    assert 'let location = _____WB$wombat$assign$function_____("location");' not in out
    assert 'let window = _____WB$wombat$assign$function_____("window");' in out
    assert "___WB_const_location" not in out


def test_a_top_level_document_write_gets_its_close(js_rewriter: JsRewriter):
    out = js_rewriter.rewrite("document.write(x);")
    assert ";document.close();" in out


def test_the_whole_wabac_fixture(js_rewriter: JsRewriter):
    # wabac.js's own combined case, expected output copied from its suite.
    out = js_rewriter.rewrite("""
  class A {}
  const B = 5;
  let C = 4;
  var D = 3;

  location = "http://example.com/2\"""")
    assert out.startswith("let C;\n")
    assert "  class A {}\n  const B = 5;\n   C = 4;\n  var D = 3;" in out
    assert ";self.___WB_const_A = A;\nself.___WB_const_B = B;\n" in out
    assert (
        "const A = self.___WB_const_A; delete self.___WB_const_A;\n"
        "const B = self.___WB_const_B; delete self.___WB_const_B;\n"
    ) in out


def test_several_declarators_on_one_line(js_rewriter: JsRewriter):
    # wabac.js: "multiple globals on same line". Each `let` name is declared
    # before the block, but the statement's keyword is removed only once.
    out = js_rewriter.rewrite(
        "let a = document.location.href, b = 1, c = 2;\nconst foo = 4, bar = 5"
    )
    assert out.startswith("let a;\nlet b;\nlet c;\n")
    assert "\n a = document.location.href, b = 1, c = 2;" in out
    assert ";self.___WB_const_foo = foo;\nself.___WB_const_bar = bar;\n" in out
    assert (
        "const foo = self.___WB_const_foo; delete self.___WB_const_foo;\n"
        "const bar = self.___WB_const_bar; delete self.___WB_const_bar;\n"
    ) in out


def test_a_carried_const_and_a_document_write_together(js_rewriter: JsRewriter):
    # wabac.js: "global + document.close append". The close goes after the
    # carrier assignment and still inside the block.
    out = js_rewriter.rewrite("\n\nconst y = document.location;\ndocument.write(x);")
    assert ";self.___WB_const_y = y;\n;document.close();" in out
    assert "const y = self.___WB_const_y; delete self.___WB_const_y;\n" in out


def test_let_var_and_const_in_one_script(js_rewriter: JsRewriter):
    # wabac.js: "add global injection".
    out = js_rewriter.rewrite("let a = document.location.href; var b = 5; const foo = 4")
    assert out.startswith("let a;\n")
    assert "\n a = document.location.href; var b = 5; const foo = 4" in out
    assert ";self.___WB_const_foo = foo;\n" in out


def test_nothing_is_carried_out_of_a_nested_scope(js_rewriter: JsRewriter):
    # Only the top level can leak a global; a const inside a function is the
    # function's business and must be left exactly as written.
    out = js_rewriter.rewrite("function f() { const inner = 1; }\nwindow.x = 1;")
    assert "___WB_const_inner" not in out
    assert "const inner = 1;" in out


def test_modern_syntax_is_still_parsed(js_rewriter: JsRewriter):
    # Optional chaining, nullish coalescing and class fields are ordinary in
    # shipped code; a parser that refuses them would silently fall back to the
    # broken behaviour on exactly the pages most likely to need this.
    out = js_rewriter.rewrite(
        "const config = window?.settings ?? {};\nclass P { #id = 1; static all = []; }"
    )
    # Only the first carried name takes the leading ";".
    assert ";self.___WB_const_config = config;\n" in out
    assert "self.___WB_const_P = P;\n" in out


def test_an_unparsable_script_is_wrapped_but_not_altered(js_rewriter: JsRewriter):
    # A script Zimi cannot read is still a script it must not corrupt.
    out = js_rewriter.rewrite("window.x = 1; const = = =;")
    assert "___WB_const_" not in out
    assert "const = = =;" in out


def test_a_script_with_no_globals_is_unchanged_around_the_block(
    js_rewriter: JsRewriter,
):
    out = js_rewriter.rewrite("window.x = 1;")
    assert not out.startswith("let ")
    assert "___WB_const_" not in out
    assert out.endswith("\n\n}")
