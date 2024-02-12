#!/usr/bin/env python3
# vim: ai ts=4 sts=4 et sw=4 nu

import pytest


@pytest.fixture(scope="function")
def html_page():
    """sample HTML content with title"""
    return """
<!DOCTYPE html>
<html lang="en-US">
<head>
    <meta charset="UTF-8" />
<meta http-equiv="X-UA-Compatible" content="IE=edge">
    <link rel="pingback" href="" />
    <title>Kiwix lets you access free knowledge - even offline</title>
    <meta name="description"
          content="Internet content for people without internet access.
          On computers, phone or raspberry hotspots: Wikipedia
          or any website, offline, anytime, for free!" />
</head>
<body>
</html>
"""
