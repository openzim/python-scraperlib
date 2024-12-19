""" URI handling module"""

import urllib.parse

from zimscraperlib.misc import first


def rebuild_uri(
    uri: urllib.parse.ParseResult,
    scheme: str | None = None,
    username: str | None = None,
    password: str | None = None,
    hostname: str | None = None,
    port: str | int | None = None,
    path: str | None = None,
    params: str | None = None,
    query: str | None = None,
    fragment: str | None = None,
) -> urllib.parse.ParseResult:
    """new ParseResult named tuple from uri with requested part updated"""
    username = first(username, uri.username)
    password = first(password, uri.password)
    hostname = first(hostname, uri.hostname)
    port = first(port, uri.port)
    netloc = (
        f"{username}{':' if password else ''}{password}"
        f"{'@' if username or password else ''}{hostname}"
        f"{':' if port else ''}{port}"
    )
    return urllib.parse.urlparse(
        urllib.parse.urlunparse(
            (
                first(scheme, uri.scheme),
                netloc,
                first(path, uri.path),
                first(params, uri.params),
                first(query, uri.query),
                first(fragment, uri.fragment),
            )
        )
    )
