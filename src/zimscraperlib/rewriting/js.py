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
Last backport of upstream changes is from wabac.js commit:
Jul 30, 2026 - 0564e36993f4044f17119e71dd7b2892512ee59c
"""

import re
from collections.abc import Callable, Iterable
from typing import Any, Literal

from zimscraperlib.rewriting.js_ast import parse_top_level
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
IMPORT_RX = re.compile(
    r"""^\s*?import\s*?[{"'*]""",
)
EXPORT_RX = re.compile(
    r"""\s*?export\s*?({([\s\w,$\n]+?)}[\s;]*|default|class)\s+""", re.MULTILINE
)
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

WORKER_GLOBAL_OVERRIDES = ["globalThis", "self", "location"]

GLOBALS_CONCAT_STR = (
    r"("
    + "|".join([r"(?:^|[^$.])\b" + x + r"\b(?:$|[^$])" for x in GLOBAL_OVERRIDES])
    + ")"
)

GLOBALS_RX = re.compile(GLOBALS_CONCAT_STR)

# This will replace `this` in code. The `_____WB$wombat$check$this$function_____`
# will "see" with wombat and may return a "wrapper" around `this`
this_rw = "_____WB$wombat$check$this$function_____(this)"


def remove_args_if_strict(
    target: str, opts: dict[str, Any] | None, offset: int, full_string: str
) -> str:
    """
    Replace 'arguments' with '[]' if the code is in strict mode.
    In strict mode, the arguments keyword is not allowed.
    """
    opts = opts or {}

    # Detect strict mode if not already set by checking for class declaration
    if "isStrict" not in opts:
        opts["isStrict"] = full_string[:offset].find("class ") >= 0  # pragma: no cover
    if opts.get("isStrict"):
        return target.replace("arguments", "[]")
    return target


def add_suffix(suffix: str) -> TransformationAction:
    """
    Create a rewrite_function which add a `suffix` to the match str.
    The suffix is added only if the match is not preceded by `.` or `$`.
    Applies strict mode transformation to handle 'arguments' keyword.
    """

    def f(m_object: re.Match[str], opts: dict[str, Any] | None) -> str:
        offset = m_object.start()
        full_string = m_object.string
        if offset > 0 and full_string[offset - 1] in ".$":
            return m_object[0]
        return m_object[0] + remove_args_if_strict(suffix, opts, offset, full_string)

    return f


def replace_this() -> TransformationAction:
    """
    Create a rewrite_function replacing "this" by `this_rw` in the matching str.
    """
    return replace("this", this_rw)


def replace_this_prop() -> TransformationAction:
    """
    Create a rewrite_function replacing "this" by `this_rw`.

    Replacement happen only if "this" is not a property of an object.
    """

    def f(m_object: re.Match[str], _opts: dict[str, Any] | None) -> str:
        offset = m_object.start()
        first_char = m_object.string[offset - 1] if offset > 0 else ""
        if first_char == "\n":
            # This detection of new line is probably buggy, plus it is hard to get the
            # intent of this, see https://github.com/openzim/warc2zim/issues/410
            return m_object[0].replace("this", ";" + this_rw)
        if first_char not in ".$":
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
        "{}).maybeHref = "
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
        # Avoid doing the below rewrite for `let/const` assignments,
        # which will break the scoping
        # See: https://github.com/webrecorder/wabac.js/issues/336
        (re.compile(r"(?:let|const)\s+location\s*="), m2str(lambda x: x)),
        # rewriting `location = ` to custom expression `(...).href =` assignement
        (
            re.compile(r"(?:^|[^$.+*/%^-])\s?\blocation\b\s*[=]\s*(?![\s\d=>])"),
            add_suffix(check_loc),
        ),
        # rewriting `return this`
        (re.compile(r"\breturn\s+this\b\s*(?![\s\w.$])"), replace_this()),
        # rewriting `this.` special porperties access on new line, with ; perpended
        # if prev chars is `\n`, or if prev is not `.` or `$`, no semi
        (
            re.compile(
                rf"[^$.]\s?\bthis\b(?=(?:\.(?:{'|'.join(GLOBAL_OVERRIDES)})\b))"
            ),
            replace_this_prop(),
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
        self.last_buff = "\n\n}"
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

    def _detect_module_or_strict(self, text: str) -> Literal["strict", "module", "lax"]:
        """
        Detect if the JavaScript code mode.
        """
        if "import" in text and IMPORT_RX.search(text):
            return "module"

        if '"use strict";' in text:
            return "strict"

        if "export" in text and EXPORT_RX.search(text):
            return "module"

        return "lax"

    def rewrite(self, text: str | bytes, opts: dict[str, Any] | None = None) -> str:
        """
        Rewrite the js code in `text`.
        """
        if isinstance(text, bytes):
            text = text.decode()

        opts = opts or {}

        if "isModule" not in opts:
            match self._detect_module_or_strict(text):
                case "module":
                    opts["isModule"] = True
                    opts["isStrict"] = True
                case "strict":
                    opts["isModule"] = False
                    opts["isStrict"] = True
                case _:
                    pass

        elif opts["isModule"]:
            opts["isStrict"] = True

        rules = REWRITE_JS_RULES[:]

        is_module = opts.get("isModule", False)

        if is_module:
            rules.append(self._get_esm_import_rule())

        self._compile_rules(rules)

        new_text = super().rewrite(text, opts)

        if is_module:
            return self._get_module_decl(GLOBAL_OVERRIDES) + new_text

        wrap_globals = GLOBALS_RX.search(text) is not None

        if opts.get("inline", False):
            new_text = new_text.replace("\n", " ")

        if wrap_globals:
            new_text = self._wrap(new_text, GLOBAL_OVERRIDES)
            if opts.get("inline", False):
                new_text = new_text.replace("\n", " ")

        return new_text

    def _wrap(self, new_text: str, overrides: list[str]) -> str:
        """Put the script inside the wombat block, and put its globals back.

        The block is a scope, so `const`, `let` and `class` declared at the top
        level of the script stop being reachable from any other script on the
        page — which is how a page that declares its data in one <script> and
        reads it from another comes out broken but silent (#329).

        So the declarations are carried across the block boundary, exactly as
        wabac.js does it:

          * `let x` is declared before the block and the keyword removed
            inside it, so the assignment inside writes the outer binding
          * `const x` and `class X` cannot be split that way, so their value
            is handed out through `self.___WB_const_x` and re-declared as a
            const after the block, and the carrier deleted
          * a name that shadows one of the wombat globals is left alone, and
            that global is dropped from the wrapper instead
          * a top-level `document.write()` gets its `document.close()`

        If the script cannot be parsed, none of this happens and the wrapper is
        exactly what it was before: a script Zimi cannot read is still a script
        it must not corrupt."""
        first_buff = self.first_buff
        last_buff = self.last_buff
        pre_scope_globals = ""
        in_scope_globals = ""
        post_scope_globals = ""

        parsed = parse_top_level(new_text) if new_text else None
        if parsed is not None:
            names: list[tuple[str, str]] = []
            exclude_overrides: set[str] = set()
            let_offsets: list[int] = []
            last_start = -1
            for decl in parsed.declarations:
                if decl.name in overrides:
                    exclude_overrides.add(decl.name)
                    continue
                if decl.kind == "class":
                    names.append((decl.name, "const"))
                elif decl.kind in ("const", "let"):
                    names.append((decl.name, decl.kind))
                    if decl.kind == "let" and last_start != decl.start:
                        let_offsets.insert(0, decl.start)
                        last_start = decl.start

            if exclude_overrides:
                first_buff = self._init_local_declaration(
                    [name for name in overrides if name not in exclude_overrides]
                )
            if parsed.has_document_write:
                last_buff = ";document.close();" + self.last_buff

            # Offsets are byte offsets into the source, and descending, so each
            # removal leaves the ones still to come valid.
            data = new_text.encode("utf-8")
            for offset in let_offsets:
                data = data[:offset] + data[offset + len("let") :]
            new_text = data.decode("utf-8", errors="replace")

            for name, kind in names:
                if kind == "const":
                    varname = f"self.___WB_const_{name}"
                    in_scope_globals += f"{varname} = {name};\n"
                    post_scope_globals += (
                        f"{kind} {name} = {varname}; delete {varname};\n"
                    )
                else:
                    pre_scope_globals += f"let {name};\n"
            if in_scope_globals:
                in_scope_globals = "\n;" + in_scope_globals
            if post_scope_globals:
                post_scope_globals = "\n" + post_scope_globals

        return (
            pre_scope_globals
            + first_buff
            + new_text
            + in_scope_globals
            + last_buff
            + post_scope_globals
        )

    def _get_esm_import_rule(self) -> TransformationRule:
        # Capture plain local values instead of closing over `self`: a closure that
        # references `self` here would end up stored in `self.rules`, creating a
        # self -> self.rules -> closure -> self reference cycle that only the cyclic
        # GC (not refcounting) can collect.
        url_rewriter = self.url_rewriter
        base_href = self.base_href
        notify_js_module = self.notify_js_module

        def get_rewriten_import_url(url: str) -> str:
            """Rewrite the import URL

            This takes into account that the result must be a relative URL, i.e. it
            cannot be 'vendor.module.js' but must be './vendor.module.js'.
            """
            url = url_rewriter(url, base_href=base_href).rewriten_url
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
                    if notify_js_module:
                        notify_js_module(
                            url_rewriter.get_item_path(
                                match.group(2), base_href=base_href
                            )
                        )
                    return (
                        f"{match.group(1)}{get_rewriten_import_url(match.group(2))}"
                        f"{match.group(3)}"
                    )

                return IMPORT_EXPORT_HTTP_RX.sub(sub_funct, m_object[0])

            return func

        return (IMPORT_EXPORT_MATCH_RX, rewrite_import())
