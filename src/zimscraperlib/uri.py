""" URI handling module"""

import urllib.parse
from typing import Union

from zimscraperlib import logger
from zimscraperlib.misc import first


def rebuild_uri(
    uri: urllib.parse.ParseResult,
    scheme: str = None,  # noqa: RUF013
    username: str = None,  # noqa: RUF013
    password: str = None,  # noqa: RUF013
    hostname: str = None,  # noqa: RUF013
    port: Union[str, int] = None,  # noqa: RUF013
    path: str = None,  # noqa: RUF013
    params: str = None,  # noqa: RUF013
    query: str = None,  # noqa: RUF013
    fragment: str = None,  # noqa: RUF013
    failsafe: bool = False,  # noqa: FBT001, FBT002
) -> urllib.parse.ParseResult:
    """new ParseResult named tuple from uri with requested part updated"""
    try:
        username = first(username, uri.username, "")
        password = first(password, uri.password, "")
        hostname = first(hostname, uri.hostname, "")
        port = first(port, uri.port, "")
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
    except Exception as exc:
        if failsafe:
            logger.error(
                f"Failed to rebuild "  # lgtm [py/clear-text-logging-sensitive-data]
                f"URI {uri} with scheme={scheme} username={username} "
                f"password={password} hostname={hostname} port={port} path={path} "
                f"params={params} query={query} fragment={fragment} - {exc}"
            )
            return uri
        raise exc
