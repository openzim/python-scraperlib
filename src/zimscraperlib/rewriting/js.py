"""JS Rewriting

This modules contains tools to rewrite JS retrieved from an online source so that it
can safely operate within a ZIM. It is based on the assumption that wombat.js will be
used for proper JS operation, intercepting all HTTP requests and rewriting them as
needed. The main purpose of the rewriting is hence simply to properly include and
configure wombat.js.

This modules assumes that:
- every HTML page in the ZIM have been properly rewriten to include wombat.js and setup
it appropriately
- a specific JS file (provided in `statics` folder) for JS modules is included in the
ZIM at `_zim_static/__wb_module_decl.js`

This code is based on https://github.com/webrecorder/wabac.js/blob/main/src/rewrite/jsrewriter.ts
Last backport of upstream changes is from Sept 13, 2025
Commit 6dd2d9ae664cfcd2ea8637d7d6c7ed7a0ca332a0
"""

import re
from collections.abc import Callable, Iterable
from typing import Any

from zimscraperlib.rewriting.rx_replacer import (
    RxRewriter,
    TransformationAction,
    TransformationRule,
    add_prefix,
    m2str,
    replace,
    replace_prefix_from,
)
from zimscraperlib.rewriting.url_rewriting import ArticleUrlRewriter, ZimPath

# The regex used to rewrite `import ...` in module code.
IMPORT_EXPORT_MATCH_RX = re.compile(
    r"""(^|;)\s*?(?:im|ex)port(?:['"\s]*(?:[\w*${}\s,]+from\s*)?['"\s]?['"\s])(?:.*?)['"\s]""",
)

# A sub regex used inside `import ...` rewrite to rewrite http url imported
IMPORT_EXPORT_HTTP_RX = re.compile(
    r"""((?:im|ex)port(?:['"\s]*(?:[\w*${}\s,]+from\s*)?['"\s]?['"\s]))((?:https?|[./]).*?)(['"\s])""",
)

# This list of global variables we want to wrap.
# We will setup the wrap only if the js script use them.
GLOBAL_OVERRIDES = [
    "window",
    "globalThis",
    "self",
    "document",
    "location",
    "top",
    "parent",
    "frames",
    "opener",
]

GLOBALS_RX = re.compile(
    r"("
    + "|".join([r"(?:^|[^$.])\b" + x + r"\b(?:$|[^$])" for x in GLOBAL_OVERRIDES])
    + ")"
)

# This will replace `this` in code. The `_____WB$wombat$check$this$function_____`
# will "see" with wombat and may return a "wrapper" around `this`
this_rw = "_____WB$wombat$check$this$function_____(this)"


def add_suffix_non_prop(suffix: str) -> TransformationAction:
    """
    Create a rewrite_function which add a `suffix` to the match str.
    The suffix is added only if the match is not preceded by `.` or `$`.
    """

    def f(m_object: re.Match[str], _opts: dict[str, Any] | None) -> str:
        offset = m_object.start()
        if offset > 0 and m_object.string[offset - 1] in ".$":
            return m_object[0]
        return m_object[0] + suffix

    return f


def replace_this() -> TransformationAction:
    """
    Create a rewrite_function replacing "this" by `this_rw` in the matching str.
    """
    return replace("this", this_rw)


def replace_this_non_prop() -> TransformationAction:
    """
    Create a rewrite_function replacing "this" by `this_rw`.

    Replacement happen only if "this" is not a property of an object.
    """

    def f(m_object: re.Match[str], _opts: dict[str, Any] | None) -> str:
        offset = m_object.start()
        prev = m_object.string[offset - 1] if offset > 0 else ""
        if prev == "\n":
            # This detection of new line is probably buggy, plus it is hard to get the
            # intent of this, see https://github.com/openzim/warc2zim/issues/410
            return m_object[0].replace("this", ";" + this_rw)
        if prev not in ".$":
            return m_object[0].replace("this", this_rw)
        return m_object[0]

    return f


def replace_import(src: str, target: str) -> TransformationAction:
    """
    Create a rewrite_function replacing `src` by `target` in the matching str.

    This "replace" function is intended to be use to replace in `import ...` as it
    adds a `import.meta.url` if we are in a module.
    """

    def f(m_object: re.Match[str], opts: dict[str, Any] | None) -> str:
        return m_object[0].replace(src, target) + (
            "import.meta.url, " if opts and opts.get("isModule") else '"", '
        )

    return f


def create_js_rules() -> list[TransformationRule]:
    """
    This function create all the transformation rules.

    A transformation rule is a tuple (Regex, rewrite_function).
    If the regex match in the rewritten script, the corresponding match object will be
    passed to rewrite_function.
    The rewrite_function must all take a `opts` dictionnary which will be the opts
    passed to the `JsRewriter.rewrite` function.
    This is mostly as if we were calling `re.sub(regex, rewrite_function, script_text)`.

    The regex will be combined and will match any non overlaping text.
    So rule to match will be applyed, potentially preventing futher rules to match.
    """

    # This will replace `location = `. This will "see" with wombat and set what have to
    # be set.
    check_loc = (
        "((self.__WB_check_loc && self.__WB_check_loc(location, arguments)) || "
        "{}).href = "
    )

    # This will replace `eval(...)`.
    eval_str = (
        "WB_wombat_runEval2((_______eval_arg, isGlobal) => { var ge = eval; return "
        "isGlobal ? ge(_______eval_arg) : "
        "eval(_______eval_arg); }).eval(this, (function() { return arguments })(),"
    )

    return [
        # rewriting `eval(...)` - invocation
        (
            re.compile(r"(?<!static)(?<!function)(?<!})(?:^|\s)\beval\s*\("),
            replace_prefix_from(eval_str, "eval"),
        ),
        (re.compile(r"\([\w]+,\s*eval\)\("), m2str(lambda _: f" {eval_str}")),
        # rewriting `x = eval` - no invocation
        (re.compile(r"[=]\s*\beval\b(?![(:.$])"), replace("eval", "self.eval")),
        (re.compile(r"var\s+self"), replace("var", "let")),
        # rewriting `.postMessage` -> `__WB_pmw(self).postMessage`
        (re.compile(r"\.postMessage\b\("), add_prefix(".__WB_pmw(self)")),
        # rewriting `location = ` to custom expression `(...).href =` assignement
        (
            re.compile(r"(?:^|[^$.+*/%^-])\s?\blocation\b\s*[=]\s*(?![\s\d=>])"),
            add_suffix_non_prop(check_loc),
        ),
        # rewriting `return this`
        (re.compile(r"\breturn\s+this\b\s*(?![\s\w.$])"), replace_this()),
        # rewriting `this.` special porperties access on new line, with ; perpended
        # if prev chars is `\n`, or if prev is not `.` or `$`, no semi
        (
            re.compile(
                rf"[^$.]\s?\bthis\b(?=(?:\.(?:{'|'.join(GLOBAL_OVERRIDES)})\b))"
            ),
            replace_this_non_prop(),
        ),
        # rewrite `= this` or `, this`
        (re.compile(r"[=,]\s*\bthis\b\s*(?![\s\w:.$])"), replace_this()),
        # rewrite `})(this_rw)`
        (re.compile(r"\}(?:\s*\))?\s*\(this\)"), replace_this()),
        # rewrite this in && or || expr
        (
            re.compile(r"[^|&][|&]{2}\s*this\b\s*(?![|\s&.$](?:[^|&]|$))"),
            replace_this(),
        ),
        # ignore `async import`.
        # As the rule will match first, it will prevent next rule matching `import` to
        # be apply to `async import`.
        (re.compile(r"async\s+import\s*\("), m2str(lambda x: x)),
        (re.compile(r"[^$.]\bimport\s*\([^)]*\)\s*\{"), m2str(lambda x: x)),
        # esm dynamic import, if found, mark as module
        (
            re.compile(r"[^$.]\bimport\s*\("),
            replace_import("import", "____wb_rewrite_import__"),
        ),
    ]


REWRITE_JS_RULES = create_js_rules()


class JsRewriter(RxRewriter):
    """
    JsRewriter is in charge of rewriting the js code stored in our zim file.
    """

    def __init__(
        self,
        url_rewriter: ArticleUrlRewriter,
        base_href: str | None,
        notify_js_module: Callable[[ZimPath], None] | None,
    ):
        super().__init__(None)
        self.first_buff = self._init_local_declaration(GLOBAL_OVERRIDES)
        self.last_buff = "\n}"
        self.url_rewriter = url_rewriter
        self.notify_js_module = notify_js_module
        self.base_href = base_href

    def _init_local_declaration(self, local_decls: Iterable[str]) -> str:
        """
        Create the prefix text to add at beginning of script.

        This will be added to script only if the script is using of the declaration in
        local_decls.
        """
        assign_func = "_____WB$wombat$assign$function_____"
        buffer = (
            f"var {assign_func} = function(name) "
            "{return (self._wb_wombat && self._wb_wombat.local_init && "
            "self._wb_wombat.local_init(name)) || self[name]; };\n"
            "if (!self.__WB_pmw) { self.__WB_pmw = function(obj) "
            "{ this.__WB_source = obj; return this; } }\n{\n"
        )
        for decl in local_decls:
            buffer += f"""let {decl} = {assign_func}("{decl}");\n"""
        buffer += "let arguments;\n"
        return buffer + "\n"

    def _get_module_decl(self, local_decls: Iterable[str]) -> str:
        """
        Create the prefix text to add at beginning of module script.

        This will be added to script only if the script is a module script.
        """
        wb_module_decl_url = self.url_rewriter.get_document_uri(
            ZimPath("_zim_static/__wb_module_decl.js"), ""
        )
        return (
            f"""import {{ {", ".join(local_decls)} }} from "{wb_module_decl_url}";\n"""
        )

    def rewrite(self, text: str | bytes, opts: dict[str, Any] | None = None) -> str:
        """
        Rewrite the js code in `text`.
        """
        if isinstance(text, bytes):
            text = text.decode()

        opts = opts or {}

        is_module = opts.get("isModule", False)

        rules = REWRITE_JS_RULES[:]

        if is_module:
            rules.append(self._get_esm_import_rule())

        self._compile_rules(rules)

        new_text = super().rewrite(text, opts)

        if is_module:
            return self._get_module_decl(GLOBAL_OVERRIDES) + new_text

        if GLOBALS_RX.search(text):
            new_text = self.first_buff + new_text + self.last_buff

        if opts.get("inline", False):
            new_text = new_text.replace("\n", " ")

        return new_text

    def _get_esm_import_rule(self) -> TransformationRule:
        def get_rewriten_import_url(url: str) -> str:
            """Rewrite the import URL

            This takes into account that the result must be a relative URL, i.e. it
            cannot be 'vendor.module.js' but must be './vendor.module.js'.
            """
            url = self.url_rewriter(url, base_href=self.base_href).rewriten_url
            if not (
                url.startswith("/") or url.startswith("./") or url.startswith("../")
            ):
                url = "./" + url
            return url

        def rewrite_import():
            def func(
                m_object: re.Match[str], _opts: dict[str, Any] | None = None
            ) -> str:
                def sub_funct(match: re.Match[str]) -> str:
                    if self.notify_js_module:
                        self.notify_js_module(
                            self.url_rewriter.get_item_path(
                                match.group(2), base_href=self.base_href
                            )
                        )
                    return (
                        f"{match.group(1)}{get_rewriten_import_url(match.group(2))}"
                        f"{match.group(3)}"
                    )

                return IMPORT_EXPORT_HTTP_RX.sub(sub_funct, m_object[0])

            return func

        return (IMPORT_EXPORT_MATCH_RX, rewrite_import())
