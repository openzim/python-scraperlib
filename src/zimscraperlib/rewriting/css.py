""" CSS Rewriting

This modules contains tools to rewrite CSS retrieved from an online source so that it
can safely operate within a ZIM, linking only to ZIM entries everytime a URL is used.

The rewriter needs to have an article url rewriter to rewrite URLs found in CSS, an
optional base href if the CSS to rewrite was found inline an HTML document which has a
base href set, and an optional flag indicating if in case of parsing error we want to
fallback to simple regex rewriting or we prefer to drop the offending rule.
"""

import re
from collections.abc import Iterable
from functools import partial
from typing import Any

from tinycss2 import (  # pyright: ignore[reportMissingTypeStubs]
    ast,
    parse_declaration_list,  # pyright: ignore[reportUnknownVariableType]
    parse_stylesheet,  # pyright: ignore[reportUnknownVariableType]
    parse_stylesheet_bytes,  # pyright: ignore[reportUnknownVariableType]
    serialize,  # pyright: ignore[reportUnknownVariableType]
)
from tinycss2.serializer import (  # pyright: ignore[reportMissingTypeStubs]
    serialize_url,  # pyright: ignore[reportUnknownVariableType]
)

from zimscraperlib import logger
from zimscraperlib.rewriting.rx_replacer import RxRewriter, TransformationRule
from zimscraperlib.rewriting.url_rewriting import ArticleUrlRewriter


class FallbackRegexCssRewriter(RxRewriter):
    """
    Fallback CSS rewriting based on regular expression.

    This is obviously way less powerful than real CSS parsing, but it allows to cope
    with CSS we failed to parse without dropping any CSS rule (problem could be just a
    parsing issue, not necessarily a bad CSS rule)
    """

    def __simple_transform(
        self,
        m_object: re.Match[str],
        _opts: dict[str, Any] | None,
        url_rewriter: ArticleUrlRewriter,
        base_href: str | None,
    ) -> str:
        """Function to apply the regex rule"""
        return "".join(
            [
                "url(",
                m_object["quote"],
                url_rewriter(m_object["url"], base_href).rewriten_url,
                m_object["quote"],
                ")",
            ]
        )

    def __init__(self, url_rewriter: ArticleUrlRewriter, base_href: str | None):
        """Create a RxRewriter adapted for CSS rules rewriting"""

        # we have only only rule, searching for url(...) functions and rewriting the
        # URL found
        rules = [
            TransformationRule(
                [
                    re.compile(
                        r"""url\((?P<quote>['"])?(?P<url>.+?)(?P=quote)(?<!\\)\)"""
                    ),
                    partial(
                        self.__simple_transform,
                        url_rewriter=url_rewriter,
                        base_href=base_href,
                    ),
                ]
            )
        ]
        super().__init__(rules)


class CssRewriter:
    """
    CSS rewriting class
    """

    def __init__(
        self,
        url_rewriter: ArticleUrlRewriter,
        base_href: str | None,
        *,
        remove_errors: bool = False,
    ):
        """
        Args:
          url_rewriter: the rewriter of URLs
          base_href: if CSS to rewrite has been found inline on an HTML page, this is
        the potential base href found in HTML document
          remove_errors: if True, we just drop bad CSS rules ; if False, we fallback to
        regex-based rewriting of the whole CSS document
        """
        self.url_rewriter = url_rewriter
        self.base_href = base_href
        self.remove_errors = remove_errors
        self.fallback_rewriter = FallbackRegexCssRewriter(url_rewriter, base_href)

    def rewrite(self, content: str | bytes) -> str:
        """
        Rewrite a 'standalone' CSS document

        'standalone' means "not inline an HTML document"
        """
        try:
            if isinstance(content, bytes):
                rules, _ = (  # pyright: ignore[reportUnknownVariableType]
                    parse_stylesheet_bytes(content)
                )

            else:
                rules = parse_stylesheet(  # pyright: ignore[reportUnknownVariableType]
                    content
                )
            self._process_list(rules)  # pyright: ignore[reportUnknownArgumentType]

            return self._serialize_rules(
                rules  # pyright: ignore[reportUnknownArgumentType]
            )
        except Exception:
            # If tinycss fail to parse css, it will generate a "Error" token.
            # Exception is raised at serialization time.
            # We try/catch the whole process to be sure anyway.
            logger.warning(
                (
                    "Css transformation fails. Fallback to regex rewriter.\n"
                    "Article path is %s"
                ),
                self.url_rewriter.article_url,
            )
            return self.fallback_rewriter.rewrite(content, {})

    def rewrite_inline(self, content: str) -> str:
        """
        Rewrite an 'inline' CSS document

        'inline' means "inline an HTML document"
        """
        try:
            rules = (  # pyright: ignore[reportUnknownVariableType]
                parse_declaration_list(content)
            )
            self._process_list(rules)  # pyright: ignore[reportUnknownArgumentType]
            return self._serialize_rules(
                rules  # pyright: ignore[reportUnknownArgumentType]
            )
        except Exception:
            # If tinycss fail to parse css, it will generate a "Error" token.
            # Exception is raised at serialization time.
            # We try/catch the whole process to be sure anyway.
            logger.warning(
                (
                    "Css transformation fails. Fallback to regex rewriter.\n"
                    "Content is `%s`"
                ),
                content,
            )
            return self.fallback_rewriter.rewrite(content, {})

    def _process_list(self, nodes: Iterable[ast.Node] | None):
        """Process a list of CSS nodes"""
        if not nodes:
            return
        for node in nodes:
            self._process_node(node)

    def _process_node(self, node: ast.Node):
        """Process one single CSS node"""
        if isinstance(
            node,
            ast.QualifiedRule
            | ast.SquareBracketsBlock
            | ast.ParenthesesBlock
            | ast.CurlyBracketsBlock,
        ):
            self._process_list(
                node.content,  # pyright: ignore[reportUnknownArgumentType, reportUnknownMemberType]
            )
        elif isinstance(node, ast.FunctionBlock):
            if node.lower_name == "url":  # pyright: ignore[reportUnknownMemberType]
                url_node: ast.Node = (  # pyright: ignore[reportUnknownVariableType]
                    node.arguments[0]  # pyright: ignore[reportUnknownMemberType]
                )
                new_url = self.url_rewriter(
                    getattr(
                        url_node,  # pyright: ignore[reportUnknownArgumentType]
                        "value",
                        "",
                    ),
                    self.base_href,
                ).rewriten_url
                setattr(  # noqa: B010
                    url_node,  # pyright: ignore[reportUnknownArgumentType]
                    "value",
                    str(new_url),
                )
                setattr(  # noqa: B010
                    url_node,  # pyright: ignore[reportUnknownArgumentType]
                    "representation",
                    f'"{serialize_url(str(new_url))}"',
                )

            else:
                self._process_list(
                    getattr(node, "arguments", []),
                )
        elif isinstance(node, ast.AtRule):
            self._process_list(
                node.prelude  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
            )
            self._process_list(
                node.content  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
            )
        elif isinstance(node, ast.Declaration):
            self._process_list(
                node.value  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
            )
        elif isinstance(node, ast.URLToken):
            new_url = self.url_rewriter(
                node.value,  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
                self.base_href,
            ).rewriten_url
            node.value = new_url
            node.representation = f"url({serialize_url(new_url)})"

    def _serialize_rules(self, rules: list[ast.Node]) -> str:
        """Serialize back all CSS rules to a string"""
        return serialize(
            [
                rule
                for rule in rules
                if not self.remove_errors or not isinstance(rule, ast.ParseError)
            ]
        )
