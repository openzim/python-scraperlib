import pytest

from zimscraperlib.rewriting.url_rewriting import (
    ArticleUrlRewriter,
    HttpUrl,
    RewriteResult,
    ZimPath,
)


class TestNormalize:

    @pytest.mark.parametrize(
        "url,zim_path",
        [
            ("https://exemple.com", "exemple.com/"),
            ("https://exemple.com/", "exemple.com/"),
            ("http://example.com/resource", "example.com/resource"),
            ("http://example.com/resource/", "example.com/resource/"),
            (
                "http://example.com/resource/folder/sub.txt",
                "example.com/resource/folder/sub.txt",
            ),
            (
                "http://example.com/resource/folder/sub",
                "example.com/resource/folder/sub",
            ),
            (
                "http://example.com/resource/folder/sub?foo=bar",
                "example.com/resource/folder/sub?foo=bar",
            ),
            (
                "http://example.com/resource/folder/sub?foo=bar#anchor1",
                "example.com/resource/folder/sub?foo=bar",
            ),
            ("http://example.com/resource/#anchor1", "example.com/resource/"),
            ("http://example.com/resource/?foo=bar", "example.com/resource/?foo=bar"),
            ("http://example.com#anchor1", "example.com/"),
            ("http://example.com?foo=bar#anchor1", "example.com/?foo=bar"),
            ("http://example.com/?foo=bar", "example.com/?foo=bar"),
            ("http://example.com/?foo=ba+r", "example.com/?foo=ba r"),
            (
                "http://example.com/?foo=ba r",
                "example.com/?foo=ba r",
            ),  # situation where the ` ` has not been properly escaped in document
            ("http://example.com/?foo=ba%2Br", "example.com/?foo=ba+r"),
            ("http://example.com/?foo=ba+%2B+r", "example.com/?foo=ba + r"),
            ("http://example.com/#anchor1", "example.com/"),
            (
                "http://example.com/some/path/http://example.com//some/path",
                "example.com/some/path/http:/example.com/some/path",
            ),
            (
                "http://example.com/some/pa?th/http://example.com//some/path",
                "example.com/some/pa?th/http:/example.com/some/path",
            ),
            (
                "http://example.com/so?me/pa?th/http://example.com//some/path",
                "example.com/so?me/pa?th/http:/example.com/some/path",
            ),
            ("http://example.com/resource?", "example.com/resource"),
            ("http://example.com/resource#", "example.com/resource"),
            ("http://user@example.com/resource", "example.com/resource"),
            ("http://user:password@example.com/resource", "example.com/resource"),
            ("http://example.com:8080/resource", "example.com/resource"),
            (
                "http://foobargooglevideo.com/videoplayback?id=1576&key=value",
                "youtube.fuzzy.replayweb.page/videoplayback?id=1576",
            ),  # Fuzzy rule is applied in addition to path transformations
            ("https://xn--exmple-cva.com", "exémple.com/"),
            ("https://xn--exmple-cva.com/", "exémple.com/"),
            ("https://xn--exmple-cva.com/resource", "exémple.com/resource"),
            ("https://exémple.com/", "exémple.com/"),
            ("https://exémple.com/resource", "exémple.com/resource"),
            # host_ip is an invalid hostname according to spec
            ("https://host_ip/", "host_ip/"),
            ("https://host_ip/resource", "host_ip/resource"),
            ("https://192.168.1.1/", "192.168.1.1/"),
            ("https://192.168.1.1/resource", "192.168.1.1/resource"),
            ("http://example.com/res%24urce", "example.com/res$urce"),
            (
                "http://example.com/resource?foo=b%24r",
                "example.com/resource?foo=b$r",
            ),
            ("http://example.com/resource@300x", "example.com/resource@300x"),
            ("http://example.com:8080/resource", "example.com/resource"),
            ("http://user@example.com:8080/resource", "example.com/resource"),
            ("http://user:password@example.com:8080/resource", "example.com/resource"),
            # the two URI below are an illustration of a potential collision (two
            # differents URI leading to the same ZIM path)
            (
                "http://tmp.kiwix.org/ci/test-website/images/urlencoding1_ico%CC%82ne-"
                "de%CC%81buter-Solidarite%CC%81-Nume%CC%81rique_1%40300x.png",
                "tmp.kiwix.org/ci/test-website/images/urlencoding1_icône-débuter-"
                "Solidarité-Numérique_1@300x.png",
            ),
            (
                "https://tmp.kiwix.org/ci/test-website/images/urlencoding1_ico%CC%82ne-"
                "de%CC%81buter-Solidarite%CC%81-Nume%CC%81rique_1@300x.png",
                "tmp.kiwix.org/ci/test-website/images/urlencoding1_icône-débuter-"
                "Solidarité-Numérique_1@300x.png",
            ),
        ],
    )
    def test_normalize(self, url: str, zim_path: str):
        assert (
            ArticleUrlRewriter.normalize(HttpUrl(url)).value == ZimPath(zim_path).value
        )


_empty_zimpath_set: set[ZimPath] = set()


class TestArticleUrlRewriter:
    @pytest.mark.parametrize(
        "original_content_url, expected_missing_zim_paths",
        [
            (
                "foo.html",
                _empty_zimpath_set,
            ),
            (
                "bar.html",
                {ZimPath("kiwix.org/a/article/bar.html")},
            ),
        ],
    )
    def test_missing_zim_paths(
        self,
        original_content_url: str,
        expected_missing_zim_paths: set[ZimPath],
    ):
        http_article_url = HttpUrl("https://kiwix.org/a/article/document.html")
        missing_zim_paths: set[ZimPath] = set()
        rewriter = ArticleUrlRewriter(
            article_url=http_article_url,
            existing_zim_paths={ZimPath("kiwix.org/a/article/foo.html")},
            missing_zim_paths=missing_zim_paths,
        )
        rewriter(original_content_url, base_href=None, rewrite_all_url=False)
        assert missing_zim_paths == expected_missing_zim_paths

    @pytest.mark.parametrize(
        "article_url, original_content_url, expected_rewrite_result, know_paths, "
        "rewrite_all_url",
        [
            (
                "https://kiwix.org/a/article/document.html",
                "foo.html",
                RewriteResult(
                    "https://kiwix.org/a/article/foo.html",
                    "foo.html",
                    ZimPath("kiwix.org/a/article/foo.html"),
                ),
                ["kiwix.org/a/article/foo.html"],
                False,
            ),
            (
                "https://kiwix.org/a/article/document.html",
                "foo.html#anchor1",
                RewriteResult(
                    "https://kiwix.org/a/article/foo.html#anchor1",
                    "foo.html#anchor1",
                    ZimPath("kiwix.org/a/article/foo.html"),
                ),
                ["kiwix.org/a/article/foo.html"],
                False,
            ),
            (
                "https://kiwix.org/a/article/document.html",
                "foo.html?foo=bar",
                RewriteResult(
                    "https://kiwix.org/a/article/foo.html?foo=bar",
                    "foo.html%3Ffoo%3Dbar",
                    ZimPath("kiwix.org/a/article/foo.html?foo=bar"),
                ),
                ["kiwix.org/a/article/foo.html?foo=bar"],
                False,
            ),
            (
                "https://kiwix.org/a/article/document.html",
                "foo.html?foo=b%24ar",
                RewriteResult(
                    "https://kiwix.org/a/article/foo.html?foo=b%24ar",
                    "foo.html%3Ffoo%3Db%24ar",
                    ZimPath("kiwix.org/a/article/foo.html?foo=b$ar"),
                ),
                ["kiwix.org/a/article/foo.html?foo=b$ar"],
                False,
            ),
            (
                "https://kiwix.org/a/article/document.html",
                "foo.html?foo=b%3Far",  # a query string with an encoded ? char in value
                RewriteResult(
                    "https://kiwix.org/a/article/foo.html?foo=b%3Far",
                    "foo.html%3Ffoo%3Db%3Far",
                    ZimPath("kiwix.org/a/article/foo.html?foo=b?ar"),
                ),
                ["kiwix.org/a/article/foo.html?foo=b?ar"],
                False,
            ),
            (
                "https://kiwix.org/a/article/document.html",
                "fo%o.html",
                RewriteResult(
                    "https://kiwix.org/a/article/fo%o.html",
                    "fo%25o.html",
                    ZimPath("kiwix.org/a/article/fo%o.html"),
                ),
                ["kiwix.org/a/article/fo%o.html"],
                False,
            ),
            (
                "https://kiwix.org/a/article/document.html",
                "foé.html",  # URL not matching RFC 3986 (found in invalid HTML doc)
                RewriteResult(
                    "https://kiwix.org/a/article/foé.html",
                    "fo%C3%A9.html",  # character is encoded so that URL match RFC 3986
                    ZimPath(
                        "kiwix.org/a/article/foé.html"
                    ),  # but ZIM path is non-encoded
                ),
                ["kiwix.org/a/article/foé.html"],
                False,
            ),
            (
                "https://kiwix.org/a/article/document.html",
                "./foo.html",
                RewriteResult(
                    "https://kiwix.org/a/article/foo.html",
                    "foo.html",
                    ZimPath("kiwix.org/a/article/foo.html"),
                ),
                ["kiwix.org/a/article/foo.html"],
                False,
            ),
            (
                "https://kiwix.org/a/article/document.html",
                "../foo.html",
                RewriteResult(
                    "https://kiwix.org/a/foo.html",
                    "https://kiwix.org/a/foo.html",  # Full URL since not in known URLs
                    ZimPath("kiwix.org/a/foo.html"),
                ),
                ["kiwix.org/a/article/foo.html"],
                False,
            ),
            (
                "https://kiwix.org/a/article/document.html",
                "../foo.html",
                RewriteResult(
                    "https://kiwix.org/a/foo.html",
                    "../foo.html",  # all URLs rewrite activated
                    ZimPath("kiwix.org/a/foo.html"),
                ),
                ["kiwix.org/a/article/foo.html"],
                True,
            ),
            (
                "https://kiwix.org/a/article/document.html",
                "../foo.html",
                RewriteResult(
                    "https://kiwix.org/a/foo.html",
                    "../foo.html",
                    ZimPath("kiwix.org/a/foo.html"),
                ),
                ["kiwix.org/a/foo.html"],
                False,
            ),
            (
                "https://kiwix.org/a/article/document.html",
                "../bar/foo.html",
                RewriteResult(
                    "https://kiwix.org/a/bar/foo.html",
                    "https://kiwix.org/a/bar/foo.html",  # Full URL since not in known
                    # URLs
                    ZimPath("kiwix.org/a/bar/foo.html"),
                ),
                ["kiwix.org/a/article/foo.html"],
                False,
            ),
            (
                "https://kiwix.org/a/article/document.html",
                "../bar/foo.html",
                RewriteResult(
                    "https://kiwix.org/a/bar/foo.html",
                    "../bar/foo.html",  # all URLs rewrite activated
                    ZimPath("kiwix.org/a/bar/foo.html"),
                ),
                ["kiwix.org/a/article/foo.html"],
                True,
            ),
            (
                "https://kiwix.org/a/article/document.html",
                "../bar/foo.html",
                RewriteResult(
                    "https://kiwix.org/a/bar/foo.html",
                    "../bar/foo.html",
                    ZimPath("kiwix.org/a/bar/foo.html"),
                ),
                ["kiwix.org/a/bar/foo.html"],
                False,
            ),
            (  # we cannot go upper than host, so '../' in excess are removed
                "https://kiwix.org/a/article/document.html",
                "../../../../../foo.html",
                RewriteResult(
                    "https://kiwix.org/foo.html",
                    "../../foo.html",
                    ZimPath("kiwix.org/foo.html"),
                ),
                ["kiwix.org/foo.html"],
                False,
            ),
            (
                "https://kiwix.org/a/article/document.html",
                "foo?param=value",
                RewriteResult(
                    "https://kiwix.org/a/article/foo?param=value",
                    "foo%3Fparam%3Dvalue",
                    ZimPath("kiwix.org/a/article/foo?param=value"),
                ),
                ["kiwix.org/a/article/foo?param=value"],
                False,
            ),
            (
                "https://kiwix.org/a/article/document.html",
                "foo?param=value%2F",
                RewriteResult(
                    "https://kiwix.org/a/article/foo?param=value%2F",
                    "foo%3Fparam%3Dvalue/",
                    ZimPath("kiwix.org/a/article/foo?param=value/"),
                ),
                ["kiwix.org/a/article/foo?param=value/"],
                False,
            ),
            (
                "https://kiwix.org/a/article/document.html",
                "foo?param=value%2Fend",
                RewriteResult(
                    "https://kiwix.org/a/article/foo?param=value%2Fend",
                    "foo%3Fparam%3Dvalue/end",
                    ZimPath("kiwix.org/a/article/foo?param=value/end"),
                ),
                ["kiwix.org/a/article/foo?param=value/end"],
                False,
            ),
            (
                "https://kiwix.org/a/article/document.html",
                "foo/",
                RewriteResult(
                    "https://kiwix.org/a/article/foo/",
                    "foo/",
                    ZimPath("kiwix.org/a/article/foo/"),
                ),
                ["kiwix.org/a/article/foo/"],
                False,
            ),
            (
                "https://kiwix.org/a/article/document.html",
                "/fo o.html",
                RewriteResult(
                    "https://kiwix.org/fo o.html",
                    "../../fo%20o.html",
                    ZimPath("kiwix.org/fo o.html"),
                ),
                ["kiwix.org/fo o.html"],
                False,
            ),
            (
                "https://kiwix.org/a/article/document.html",
                "/fo+o.html",
                RewriteResult(
                    "https://kiwix.org/fo+o.html",
                    "../../fo%2Bo.html",
                    ZimPath("kiwix.org/fo+o.html"),
                ),
                ["kiwix.org/fo+o.html"],
                False,
            ),
            (
                "https://kiwix.org/a/article/document.html",
                "/fo%2Bo.html",
                RewriteResult(
                    "https://kiwix.org/fo%2Bo.html",
                    "../../fo%2Bo.html",
                    ZimPath("kiwix.org/fo+o.html"),
                ),
                ["kiwix.org/fo+o.html"],
                False,
            ),
            (
                "https://kiwix.org/a/article/document.html",
                "/foo.html?param=val+ue",
                RewriteResult(
                    "https://kiwix.org/foo.html?param=val+ue",
                    "../../foo.html%3Fparam%3Dval%20ue",
                    ZimPath("kiwix.org/foo.html?param=val ue"),
                ),
                ["kiwix.org/foo.html?param=val ue"],
                False,
            ),
            (
                "https://kiwix.org/a/article/document.html",
                "/fo~o.html",
                RewriteResult(
                    "https://kiwix.org/fo~o.html",
                    "../../fo~o.html",
                    ZimPath("kiwix.org/fo~o.html"),
                ),
                ["kiwix.org/fo~o.html"],
                False,
            ),
            (
                "https://kiwix.org/a/article/document.html",
                "/fo-o.html",
                RewriteResult(
                    "https://kiwix.org/fo-o.html",
                    "../../fo-o.html",
                    ZimPath("kiwix.org/fo-o.html"),
                ),
                ["kiwix.org/fo-o.html"],
                False,
            ),
            (
                "https://kiwix.org/a/article/document.html",
                "/fo_o.html",
                RewriteResult(
                    "https://kiwix.org/fo_o.html",
                    "../../fo_o.html",
                    ZimPath("kiwix.org/fo_o.html"),
                ),
                ["kiwix.org/fo_o.html"],
                False,
            ),
            (
                "https://kiwix.org/a/article/document.html",
                "/fo%7Eo.html",  # must not be encoded / must be decoded (RFC 3986 #2.3)
                RewriteResult(
                    "https://kiwix.org/fo%7Eo.html",
                    "../../fo~o.html",
                    ZimPath("kiwix.org/fo~o.html"),
                ),
                ["kiwix.org/fo~o.html"],
                False,
            ),
            (
                "https://kiwix.org/a/article/document.html",
                "/fo%2Do.html",  # must not be encoded / must be decoded (RFC 3986 #2.3)
                RewriteResult(
                    "https://kiwix.org/fo%2Do.html",
                    "../../fo-o.html",
                    ZimPath("kiwix.org/fo-o.html"),
                ),
                ["kiwix.org/fo-o.html"],
                False,
            ),
            (
                "https://kiwix.org/a/article/document.html",
                "/fo%5Fo.html",  # must not be encoded / must be decoded (RFC 3986 #2.3)
                RewriteResult(
                    "https://kiwix.org/fo%5Fo.html",
                    "../../fo_o.html",
                    ZimPath("kiwix.org/fo_o.html"),
                ),
                ["kiwix.org/fo_o.html"],
                False,
            ),
            (
                "https://kiwix.org/a/article/document.html",
                "/foo%2Ehtml",  # must not be encoded / must be decoded (RFC 3986 #2.3)
                RewriteResult(
                    "https://kiwix.org/foo%2Ehtml",
                    "../../foo.html",
                    ZimPath("kiwix.org/foo.html"),
                ),
                ["kiwix.org/foo.html"],
                False,
            ),
            (
                "https://kiwix.org/a/article/document.html",
                "#anchor1",
                RewriteResult(
                    "https://kiwix.org/a/article/document.html#anchor1",
                    "#anchor1",
                    None,
                ),
                ["kiwix.org/a/article/document.html"],
                False,
            ),
            (
                "https://kiwix.org/a/article/",
                "#anchor1",
                RewriteResult(
                    "https://kiwix.org/a/article/#anchor1",
                    "#anchor1",
                    None,
                ),
                ["kiwix.org/a/article/"],
                False,
            ),
            (
                "https://kiwix.org/a/article/",
                "../article/",
                RewriteResult(
                    "https://kiwix.org/a/article/",
                    "./",
                    ZimPath("kiwix.org/a/article/"),
                ),
                ["kiwix.org/a/article/"],
                False,
            ),
        ],
    )
    def test_relative_url(
        self,
        article_url: str,
        know_paths: list[str],
        original_content_url: str,
        expected_rewrite_result: RewriteResult,
        *,
        rewrite_all_url: bool,
    ):
        http_article_url = HttpUrl(article_url)
        rewriter = ArticleUrlRewriter(
            article_url=http_article_url,
            existing_zim_paths={ZimPath(path) for path in know_paths},
        )
        assert (
            rewriter(
                original_content_url, base_href=None, rewrite_all_url=rewrite_all_url
            )
            == expected_rewrite_result
        )

    @pytest.mark.parametrize(
        "article_url, original_content_url, expected_rewrite_result, know_paths, "
        "rewrite_all_url",
        [
            (
                "https://kiwix.org/a/article/document.html",
                "/foo.html",
                RewriteResult(
                    "https://kiwix.org/foo.html",
                    "../../foo.html",
                    ZimPath("kiwix.org/foo.html"),
                ),
                ["kiwix.org/foo.html"],
                False,
            ),
            (
                "https://kiwix.org/a/article/document.html",
                "/bar.html",
                RewriteResult(
                    "https://kiwix.org/bar.html",
                    "https://kiwix.org/bar.html",  # Full URL since not in known URLs
                    ZimPath("kiwix.org/bar.html"),
                ),
                ["kiwix.org/foo.html"],
                False,
            ),
            (
                "https://kiwix.org/a/article/document.html",
                "/bar.html",
                RewriteResult(
                    "https://kiwix.org/bar.html",
                    "../../bar.html",  # all URLs rewrite activated
                    ZimPath("kiwix.org/bar.html"),
                ),
                ["kiwix.org/foo.html"],
                True,
            ),
        ],
    )
    def test_absolute_path_url(
        self,
        article_url: str,
        know_paths: list[str],
        original_content_url: str,
        expected_rewrite_result: RewriteResult,
        *,
        rewrite_all_url: bool,
    ):
        http_article_url = HttpUrl(article_url)
        rewriter = ArticleUrlRewriter(
            article_url=http_article_url,
            existing_zim_paths={ZimPath(path) for path in know_paths},
        )
        assert (
            rewriter(
                original_content_url, base_href=None, rewrite_all_url=rewrite_all_url
            )
            == expected_rewrite_result
        )

    @pytest.mark.parametrize(
        "article_url, original_content_url, expected_rewrite_result, know_paths, "
        "rewrite_all_url",
        [
            (
                "https://kiwix.org/a/article/document.html",
                "//kiwix.org/foo.html",
                RewriteResult(
                    "https://kiwix.org/foo.html",
                    "../../foo.html",
                    ZimPath("kiwix.org/foo.html"),
                ),
                ["kiwix.org/foo.html"],
                False,
            ),
            (
                "https://kiwix.org/a/article/document.html",
                "//kiwix.org/bar.html",
                RewriteResult(
                    "https://kiwix.org/bar.html",
                    "https://kiwix.org/bar.html",  # Full URL since not in known URLs
                    ZimPath("kiwix.org/bar.html"),
                ),
                ["kiwix.org/foo.html"],
                False,
            ),
            (
                "https://kiwix.org/a/article/document.html",
                "//kiwix.org/bar.html",
                RewriteResult(
                    "https://kiwix.org/bar.html",
                    "../../bar.html",  # all URLs rewrite activated
                    ZimPath("kiwix.org/bar.html"),
                ),
                ["kiwix.org/foo.html"],
                True,
            ),
            (
                "https://kiwix.org/a/article/document.html",
                "//acme.com/foo.html",
                RewriteResult(
                    "https://acme.com/foo.html",
                    "../../../acme.com/foo.html",
                    ZimPath("acme.com/foo.html"),
                ),
                ["acme.com/foo.html"],
                False,
            ),
            (
                "http://kiwix.org/a/article/document.html",
                "//acme.com/bar.html",
                RewriteResult(
                    "http://acme.com/bar.html",
                    "http://acme.com/bar.html",  # Full URL since not in known URLs
                    ZimPath("acme.com/bar.html"),
                ),
                ["kiwix.org/foo.html"],
                False,
            ),
            (
                "https://kiwix.org/a/article/document.html",
                "//acme.com/bar.html",
                RewriteResult(
                    "https://acme.com/bar.html",
                    "../../../acme.com/bar.html",  # all URLs rewrite activated
                    ZimPath("acme.com/bar.html"),
                ),
                ["kiwix.org/foo.html"],
                True,
            ),
            (  # puny-encoded host is transformed into url-encoded value
                "https://kiwix.org/a/article/document.html",
                "//xn--exmple-cva.com/a/article/document.html",
                RewriteResult(
                    "https://xn--exmple-cva.com/a/article/document.html",
                    "../../../ex%C3%A9mple.com/a/article/document.html",
                    ZimPath("exémple.com/a/article/document.html"),
                ),
                ["exémple.com/a/article/document.html"],
                False,
            ),
            (  # host who should be puny-encoded ir transformed into url-encoded value
                "https://kiwix.org/a/article/document.html",
                "//exémple.com/a/article/document.html",
                RewriteResult(
                    "https://exémple.com/a/article/document.html",
                    "../../../ex%C3%A9mple.com/a/article/document.html",
                    ZimPath("exémple.com/a/article/document.html"),
                ),
                ["exémple.com/a/article/document.html"],
                False,
            ),
        ],
    )
    def test_absolute_scheme_url(
        self,
        article_url: str,
        know_paths: list[str],
        original_content_url: str,
        expected_rewrite_result: RewriteResult,
        *,
        rewrite_all_url: bool,
    ):
        http_article_url = HttpUrl(article_url)
        rewriter = ArticleUrlRewriter(
            article_url=http_article_url,
            existing_zim_paths={ZimPath(path) for path in know_paths},
        )
        assert (
            rewriter(
                original_content_url, base_href=None, rewrite_all_url=rewrite_all_url
            )
            == expected_rewrite_result
        )

    @pytest.mark.parametrize(
        "article_url, original_content_url, expected_rewriten_result, know_paths, "
        "rewrite_all_url",
        [
            pytest.param(
                "https://kiwix.org/a/article/document.html",
                "https://foo.org/a/article/document.html",
                RewriteResult(
                    "https://foo.org/a/article/document.html",
                    "../../../foo.org/a/article/document.html",
                    ZimPath("foo.org/a/article/document.html"),
                ),
                ["foo.org/a/article/document.html"],
                False,
                id="simple",
            ),
            pytest.param(
                "https://kiwix.org/a/article/document.html",
                "http://foo.org/a/article/document.html",
                RewriteResult(
                    "http://foo.org/a/article/document.html",
                    "../../../foo.org/a/article/document.html",
                    ZimPath("foo.org/a/article/document.html"),
                ),
                ["foo.org/a/article/document.html"],
                False,
                id="http_https",
            ),
            pytest.param(
                "http://kiwix.org/a/article/document.html",
                "https://foo.org/a/article/document.html",
                RewriteResult(
                    "https://foo.org/a/article/document.html",
                    "../../../foo.org/a/article/document.html",
                    ZimPath("foo.org/a/article/document.html"),
                ),
                ["foo.org/a/article/document.html"],
                False,
                id="https_http",
            ),
            pytest.param(
                "http://kiwix.org/a/article/document.html",
                "https://user:password@foo.org:8080/a/article/document.html",
                RewriteResult(
                    "https://user:password@foo.org:8080/a/article/document.html",
                    "../../../foo.org/a/article/document.html",
                    ZimPath("foo.org/a/article/document.html"),
                ),
                ["foo.org/a/article/document.html"],
                False,
                id="user_pass",
            ),
            pytest.param(  # Full URL since not in known URLs
                "https://kiwix.org/a/article/document.html",
                "https://foo.org/a/article/document.html",
                RewriteResult(
                    "https://foo.org/a/article/document.html",
                    "https://foo.org/a/article/document.html",
                    ZimPath("foo.org/a/article/document.html"),
                ),
                ["kiwix.org/a/article/foo/"],
                False,
                id="not_known",
            ),
            pytest.param(  # all URLs rewrite activated
                "https://kiwix.org/a/article/document.html",
                "https://foo.org/a/article/document.html",
                RewriteResult(
                    "https://foo.org/a/article/document.html",
                    "../../../foo.org/a/article/document.html",
                    ZimPath("foo.org/a/article/document.html"),
                ),
                ["kiwix.org/a/article/foo/"],
                True,
                id="not_known_rewrite_all",
            ),
            pytest.param(  # puny-encoded host is transformed into url-encoded value
                "https://kiwix.org/a/article/document.html",
                "https://xn--exmple-cva.com/a/article/document.html",
                RewriteResult(
                    "https://xn--exmple-cva.com/a/article/document.html",
                    "../../../ex%C3%A9mple.com/a/article/document.html",
                    ZimPath("exémple.com/a/article/document.html"),
                ),
                ["exémple.com/a/article/document.html"],
                False,
                id="punny_encoded",
            ),
            pytest.param(  # host who should be puny-encoded is transformed into
                # url-encoded value
                "https://kiwix.org/a/article/document.html",
                "https://exémple.com/a/article/document.html",
                RewriteResult(
                    "https://exémple.com/a/article/document.html",
                    "../../../ex%C3%A9mple.com/a/article/document.html",
                    ZimPath("exémple.com/a/article/document.html"),
                ),
                ["exémple.com/a/article/document.html"],
                False,
                id="should_be_punny_encoded",
            ),
        ],
    )
    def test_absolute_url(
        self,
        article_url: str,
        know_paths: list[str],
        original_content_url: str,
        expected_rewriten_result: RewriteResult,
        *,
        rewrite_all_url: bool,
    ):
        http_article_url = HttpUrl(article_url)
        rewriter = ArticleUrlRewriter(
            article_url=http_article_url,
            existing_zim_paths={ZimPath(path) for path in know_paths},
        )
        assert (
            rewriter(
                original_content_url, base_href=None, rewrite_all_url=rewrite_all_url
            )
            == expected_rewriten_result
        )

    @pytest.mark.parametrize(
        "original_content_url, rewrite_all_url",
        [
            ("data:0548datacontent", False),
            ("blob:exemple.com/url", False),
            ("mailto:bob@acme.com", False),
            ("tel:+33.1.12.12.23", False),
            ("data:0548datacontent", True),
            ("blob:exemple.com/url", True),
            ("mailto:bob@acme.com", True),
            ("tel:+33.1.12.12.23", True),
        ],
    )
    # other schemes are never rewritten, even when rewrite_all_url is true
    def test_no_rewrite_other_schemes(
        self, original_content_url: str, *, rewrite_all_url: bool
    ):
        article_url = HttpUrl("https://kiwix.org/a/article/document.html")
        rewriter = ArticleUrlRewriter(article_url=article_url)
        assert rewriter(
            original_content_url, base_href=None, rewrite_all_url=rewrite_all_url
        ) == RewriteResult(original_content_url, original_content_url, None)

    @pytest.mark.parametrize(
        "original_content_url, know_path, base_href, expected_rewriten_result",
        [
            pytest.param(
                "foo.html",
                "kiwix.org/a/article/foo.html",
                None,
                RewriteResult(
                    "https://kiwix.org/a/article/foo.html",
                    "foo.html",
                    ZimPath("kiwix.org/a/article/foo.html"),
                ),
                id="no_base",
            ),
            pytest.param(
                "foo.html",
                "kiwix.org/a/foo.html",
                "../",
                RewriteResult(
                    "https://kiwix.org/a/foo.html",
                    "../foo.html",
                    ZimPath("kiwix.org/a/foo.html"),
                ),
                id="parent_base",
            ),
            pytest.param(
                "foo.html",
                "kiwix.org/a/bar/foo.html",
                "../bar/",
                RewriteResult(
                    "https://kiwix.org/a/bar/foo.html",
                    "../bar/foo.html",
                    ZimPath("kiwix.org/a/bar/foo.html"),
                ),
                id="base_in_another_folder",
            ),
            pytest.param(
                "foo.html",
                "www.example.com/foo.html",
                "https://www.example.com/",
                RewriteResult(
                    "https://www.example.com/foo.html",
                    "../../../www.example.com/foo.html",
                    ZimPath("www.example.com/foo.html"),
                ),
                id="base_on_absolute_url",
            ),
        ],
    )
    def test_base_href(
        self,
        original_content_url: str,
        know_path: str,
        base_href: str,
        expected_rewriten_result: str,
    ):
        rewriter = ArticleUrlRewriter(
            article_url=HttpUrl("https://kiwix.org/a/article/document.html"),
            existing_zim_paths={ZimPath(know_path)},
        )
        assert (
            rewriter(original_content_url, base_href=base_href, rewrite_all_url=False)
            == expected_rewriten_result
        )


class CustomRewriter(ArticleUrlRewriter):
    """Sample class using the rewriting result to process items to download

    This mimic this typical usage by mindtouch scraper so that we check this is still
    working as expected since it is the only usage so far of this information
    """

    def __init__(
        self,
        *,
        article_url: HttpUrl,
        article_path: ZimPath | None = None,
        existing_zim_paths: set[ZimPath] | None = None,
        missing_zim_paths: set[ZimPath] | None = None,
    ):
        super().__init__(
            article_url=article_url,
            article_path=article_path,
            existing_zim_paths=existing_zim_paths,
            missing_zim_paths=missing_zim_paths,
        )
        self.items_to_download: dict[ZimPath, set[HttpUrl]] = {}

    def __call__(
        self, item_url: str, base_href: str | None, *, rewrite_all_url: bool = True
    ) -> RewriteResult:
        result = super().__call__(item_url, base_href, rewrite_all_url=rewrite_all_url)
        if result.zim_path is None:
            return result
        if self.existing_zim_paths and result.zim_path not in self.existing_zim_paths:
            return result
        if result.zim_path in self.items_to_download:
            self.items_to_download[result.zim_path].add(HttpUrl(result.absolute_url))
        else:
            self.items_to_download[result.zim_path] = {HttpUrl(result.absolute_url)}
        return result


class TestCustomRewriter:

    def test_items_to_download(self):
        rewriter = CustomRewriter(
            article_url=HttpUrl("https://kiwix.org/a/article/document.html"),
            existing_zim_paths={
                ZimPath("kiwix.org/a/article/foo.html"),
                ZimPath("kiwix.org/a/article/bar.html"),
            },
        )
        rewriter("foo.html#anchor1", base_href=None, rewrite_all_url=False)
        rewriter("foo.html#anchor2", base_href=None, rewrite_all_url=False)
        rewriter("bar.html", base_href=None, rewrite_all_url=False)
        rewriter("missing.html", base_href=None, rewrite_all_url=False)
        assert rewriter.items_to_download == {
            ZimPath("kiwix.org/a/article/foo.html"): {
                HttpUrl("https://kiwix.org/a/article/foo.html#anchor1"),
                HttpUrl("https://kiwix.org/a/article/foo.html#anchor2"),
            },
            ZimPath("kiwix.org/a/article/bar.html"): {
                HttpUrl("https://kiwix.org/a/article/bar.html")
            },
        }


class TestHttpUrl:

    @pytest.mark.parametrize(
        "http_url",
        [("https://bob@acme.com"), ("http://bob@acme.com"), ("hTtPs://bob@acme.com")],
    )
    def test_good_http_urls(self, http_url: str):
        HttpUrl(http_url)

    @pytest.mark.parametrize(
        "http_url",
        [("mailto:bob@acme.com"), ("tel:+41.34.34"), ("mailto:https://bob@acme.com")],
    )
    def test_bad_http_urls_scheme(self, http_url: str):
        with pytest.raises(ValueError, match="Incorrect HttpUrl scheme in value"):
            HttpUrl(http_url)

    def test_http_urls_eq(self):
        assert HttpUrl("http://bob@acme.com") == HttpUrl("http://bob@acme.com")

    def test_http_urls_hash(self):
        assert (
            HttpUrl("http://bob@acme.com").__hash__()
            == HttpUrl("http://bob@acme.com").__hash__()
        )

    def test_http_urls_str(self):
        assert str(HttpUrl("http://bob@acme.com")) == "HttpUrl(http://bob@acme.com)"
        assert f'{HttpUrl("http://bob@acme.com")}' == "HttpUrl(http://bob@acme.com)"

    def test_bad_http_urls_no_host(self):
        with pytest.raises(ValueError, match="Unsupported empty hostname in value"):
            HttpUrl("https:///bob/index.html")

    def test_bad_http_urls_no_upper(self):
        with pytest.raises(
            ValueError, match="Unsupported upper-case chars in hostname"
        ):
            HttpUrl("https://aCmE.COM/index.html")


class TestZimPath:

    @pytest.mark.parametrize(
        "path",
        [
            ("content/index.html"),
            ("index.html"),
        ],
    )
    def test_good_zim_path(self, path: str):
        ZimPath(path)

    @pytest.mark.parametrize(
        "path",
        [
            ("https://bob@acme.com"),
            ("http://bob@acme.com"),
            ("mailto:bob@acme.com"),
            ("tel:+41.34.34"),
            ("mailto:https://bob@acme.com"),
        ],
    )
    def test_bad_zim_path_scheme(self, path: str):
        with pytest.raises(ValueError, match="Unexpected scheme in value"):
            ZimPath(path)

    @pytest.mark.parametrize(
        "path",
        [
            ("//acme.com/content/index.html"),
        ],
    )
    def test_bad_zim_path_hostname(self, path: str):
        with pytest.raises(ValueError, match="Unexpected hostname in value"):
            ZimPath(path)

    @pytest.mark.parametrize(
        "path",
        [
            ("//bob@/content/index.html"),
        ],
    )
    def test_bad_zim_path_user(self, path: str):
        with pytest.raises(ValueError, match="Unexpected username in value"):
            ZimPath(path)

    @pytest.mark.parametrize(
        "path",
        [
            ("//:pass@/content/index.html"),
        ],
    )
    def test_bad_zim_path_pass(self, path: str):
        with pytest.raises(ValueError, match="Unexpected password in value"):
            ZimPath(path)

    def test_zim_path_eq(self):
        assert ZimPath("content/index.html") == ZimPath("content/index.html")

    def test_zim_path_hash(self):
        assert (
            ZimPath("content/index.html").__hash__()
            == ZimPath("content/index.html").__hash__()
        )

    def test_zim_path_str(self):
        assert str(ZimPath("content/index.html")) == "ZimPath(content/index.html)"
        assert f'{ZimPath("content/index.html")}' == "ZimPath(content/index.html)"
