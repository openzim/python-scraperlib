"""The little bit of JavaScript parsing the JS rewriter needs.

`js.py` wraps a script in a block so wombat can shadow `window`, `document`
and friends. A block is a scope, so every top-level `const`, `let` and `class`
in the script becomes block-scoped too, and stops being visible to any other
script on the page. wabac.js solves this by parsing the script and hoisting
those names back out; this module is the parsing half of that, kept behind one
function so the choice of parser is one import to change.

Only the top level matters. Nothing nested can leak a global, so this never
walks into a function body, and it answers three questions:

  * which `const`, `let`, `var` and `class` names the script declares at the
    top level, and of what kind
  * where each declaration starts, so a `let` keyword can be removed
  * whether the script calls `document.write()` at the top level

Why tree-sitter and not a pure-Python parser: the scripts this runs on are
whatever the live web served. `esprima` (the obvious pure-Python choice) is
ES2017 and refuses optional chaining, class fields and `for await`, all of
which are ordinary in shipped code today; tree-sitter parses them, and is
error-tolerant besides, so a script it cannot fully understand still yields
the declarations it could read rather than an exception.
"""

from __future__ import annotations

from dataclasses import dataclass

import tree_sitter_javascript
from tree_sitter import Language, Node, Parser

__all__ = ["Declaration", "TopLevel", "node_text", "parse_top_level"]

_PARSER = Parser(Language(tree_sitter_javascript.language()))


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


def node_text(node: Node | None, source: bytes) -> str:
    """The source a node covers. A missing node reads as no text, so callers
    can ask for an optional field without a guard at every site."""
    if node is None:
        return ""
    return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def _identifiers(node: Node, source: bytes) -> list[str]:
    """The plain identifiers a declaration binds.

    Destructuring (`const {a, b} = x`) is deliberately skipped, exactly as
    wabac.js skips anything whose id is not an Identifier: hoisting a
    destructured binding would mean rebuilding the pattern, and the names it
    binds are rare enough at the top level of a script to be worth leaving
    alone rather than getting subtly wrong."""
    names: list[str] = []
    for child in node.named_children:
        name = child.child_by_field_name("name")
        if name is not None and name.type == "identifier":
            names.append(node_text(name, source))
    return names


def _is_document_write(node: Node, source: bytes) -> bool:
    if node.type != "expression_statement" or not node.named_children:
        return False
    call = node.named_children[0]
    if call.type != "call_expression":
        return False
    callee = call.child_by_field_name("function")
    if callee is None or callee.type != "member_expression":
        return False
    # A member expression always has both fields; anything else is a parser
    # surprise, and parse_top_level's own net catches those.
    obj = callee.child_by_field_name("object")
    prop = callee.child_by_field_name("property")
    return node_text(obj, source) == "document" and node_text(prop, source) == "write"


def parse_top_level(text: str) -> TopLevel | None:
    """Read a script's top-level declarations, or None when it cannot be read.

    None means "no opinion", and the caller leaves the script alone — which is
    what happened to every script before this existed. wabac.js wraps its whole
    parseGlobals in a try/catch for the same reason, and so does this: nothing
    here may throw into a scrape."""
    try:
        source = text.encode("utf-8")
        root = _PARSER.parse(source).root_node
        declarations: list[Declaration] = []
        has_document_write = False
        for node in root.named_children:
            if node.type == "lexical_declaration":
                # `const` or `let` — `using` has its own node type.
                kind = node_text(node.children[0], source)
                for name in _identifiers(node, source):
                    declarations.append(Declaration(name, kind, node.start_byte))
            elif node.type == "variable_declaration":
                for name in _identifiers(node, source):
                    declarations.append(Declaration(name, "var", node.start_byte))
            elif node.type == "class_declaration":
                name_node = node.child_by_field_name("name")
                declarations.append(
                    Declaration(node_text(name_node, source), "class", node.start_byte)
                )
            elif not has_document_write and _is_document_write(node, source):
                has_document_write = True
        return TopLevel(
            declarations=declarations, has_document_write=has_document_write
        )
    except Exception:
        return None
