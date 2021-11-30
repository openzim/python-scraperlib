import urllib.parse

import pytest

from zimscraperlib.uri import rebuild_uri


@pytest.mark.parametrize(
    "uri,changes,expected",
    [
        ("http://localhost", {}, "http://localhost"),
        ("http://localhost", {"scheme": "tel"}, "tel://localhost"),
        ("http://localhost", {"username": "user"}, "http://user@localhost"),
        ("http://localhost", {"password": "pass"}, "http://:pass@localhost"),
        ("http://localhost", {"hostname": "google.com"}, "http://google.com"),
        ("http://localhost", {"port": "8080"}, "http://localhost:8080"),
        ("http://localhost", {"path": "/welcome"}, "http://localhost/welcome"),
        ("http://localhost", {"params": "me"}, "http://localhost/;me"),
        ("http://localhost", {"query": "token=32"}, "http://localhost?token=32"),
        ("http://localhost", {"fragment": "top"}, "http://localhost#top"),
        (
            "http://localhost",
            {
                "scheme": "https",
                "username": "user",
                "password": "pass",
                "hostname": "google.com",
                "port": "8080",
                "path": "settings",
                "params": "mine",
                "query": "lang=fr&hl=true",
                "fragment": "top",
            },
            "https://user:pass@google.com:8080/settings;mine?lang=fr&hl=true#top",
        ),
        (
            "https://user:pass@google.com:8080/settings;mine?lang=fr&hl=true#top",
            {
                "scheme": "http",
                "username": "",
                "password": "",
                "hostname": "localhost",
                "port": "",
                "path": "",
                "params": "",
                "query": "",
                "fragment": "",
            },
            "http://localhost",
        ),
    ],
)
def test_rebuild_uri(uri, changes, expected):
    assert rebuild_uri(urllib.parse.urlparse(uri), **changes).geturl() == expected


@pytest.mark.parametrize(
    "uri,changes",
    [
        ("http://localhost", {"scheme": 123}),
    ],
)
def test_rebuild_uri_failure(uri, changes):
    with pytest.raises(TypeError):
        rebuild_uri(urllib.parse.urlparse(uri), **changes)


@pytest.mark.parametrize(
    "uri,changes",
    [
        ("http://localhost", {"scheme": 123}),
    ],
)
def test_rebuild_uri_failsafe(uri, changes):
    puri = urllib.parse.urlparse(uri)
    assert rebuild_uri(puri, **changes, failsafe=True) == puri
