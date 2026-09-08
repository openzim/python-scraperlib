"""The little bit of JavaScript parsing the JS rewriter needs.

`js.py` wraps a script in a block so wombat can shadow `window`, `document`
and friends. A block is a scope, so every top-level `const`, `let` and `class`
in the script becomes block-scoped too, and stops being visible to any other
script on the page. wabac.js solves this by parsing the script and hoisting
those names back out; this module is the parsing half of that, kept behind one
function so the choice of parser is one import to change.

Only the top level matters. Nothing nested can leak a global, so this never
walks into a function body, and it answers four questions:

  * which `const` / `let` / `class` names the script declares at the top level
  * where each `let` statement starts, so the keyword can be removed
  * which of the names shadow a global the wrapper is about to declare
  * whether the script calls `document.write()` at the top level

Why tree-sitter and not a pure-Python parser: the scripts this runs on are
whatever the live web served. `esprima` (the obvious pure-Python choice) is
ES2017 and refuses optional chaining, class fields and `for await`, all of
which are ordinary in shipped code today; tree-sitter parses them, and is
error-tolerant besides, so a script it cannot fully understand still yields
the declarations it could read rather than an exception.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass

__all__ = ["Declaration", "TopLevel", "parse_top_level", "parser_available"]


@dataclass(frozen=True)
class Declaration:
    """One name a script declares at its top level."""

    name: str
    kind: str  # "const" | "let" | "var" | "class"
    start: int  # byte offset of the statement that declares it


@dataclass(frozen=True)
class TopLevel:
    declarations: list[Declaration]
    has_document_write: bool


@functools.lru_cache(maxsize=1)
def _parser():
    """The parser, built once. None when tree-sitter is not installed, which
    is not an error: the rewriter falls back to its unparsed behaviour."""
    try:
        import tree_sitter_javascript
        from tree_sitter import Language, Parser

        return Parser(Language(tree_sitter_javascript.language()))
    except Exception:  # noqa: BLE001 - any import or ABI trouble means no parser
        return None


def parser_available() -> bool:
    return _parser() is not None


def _text(node, source: bytes) -> str:
    return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def _identifiers(node, source: bytes) -> list[str]:
    """The plain identifiers a declarator binds.

    Destructuring (`const {a, b} = x`) is deliberately skipped, exactly as
    wabac.js skips anything whose id is not an Identifier: hoisting a
    destructured binding would mean rebuilding the pattern, and the names it
    binds are rare enough at the top level of a script to be worth leaving
    alone rather than getting subtly wrong."""
    names = []
    for child in node.named_children:
        if child.type == "variable_declarator":
            first = child.child_by_field_name("name")
            if first is not None and first.type == "identifier":
                names.append(_text(first, source))
    return names


def _is_document_write(node, source: bytes) -> bool:
    if node.type != "expression_statement":
        return False
    call = node.named_children[0] if node.named_children else None
    if call is None or call.type != "call_expression":
        return False
    callee = call.child_by_field_name("function")
    if callee is None or callee.type != "member_expression":
        return False
    obj = callee.child_by_field_name("object")
    prop = callee.child_by_field_name("property")
    return (
        obj is not None
        and prop is not None
        and obj.type == "identifier"
        and prop.type == "property_identifier"
        and _text(obj, source) == "document"
        and _text(prop, source) == "write"
    )


def parse_top_level(text: str) -> TopLevel | None:
    """Read a script's top-level declarations, or None when it cannot be read.

    None means "no opinion" and the caller must fall back to leaving the
    script alone, which is what happened before this existed."""
    parser = _parser()
    if parser is None:
        return None
    source = text.encode("utf-8")
    try:
        tree = parser.parse(source)
    except Exception:  # noqa: BLE001 - a parser crash must not fail a scrape
        return None
    root = tree.root_node
    if root is None:
        return None

    declarations: list[Declaration] = []
    has_document_write = False
    for node in root.named_children:
        if node.type == "lexical_declaration":
            # `const` / `let`: the keyword is the first token of the statement.
            kind = _text(node.children[0], source) if node.children else ""
            if kind in ("const", "let"):
                for name in _identifiers(node, source):
                    declarations.append(Declaration(name, kind, node.start_byte))
        elif node.type == "variable_declaration":
            for name in _identifiers(node, source):
                declarations.append(Declaration(name, "var", node.start_byte))
        elif node.type == "class_declaration":
            named = node.child_by_field_name("name")
            if named is not None:
                declarations.append(
                    Declaration(_text(named, source), "class", node.start_byte)
                )
        elif not has_document_write and _is_document_write(node, source):
            has_document_write = True

    return TopLevel(declarations=declarations, has_document_write=has_document_write)
