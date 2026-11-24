import io
import uuid

import pytest


@pytest.fixture(scope="function")
def random_id() -> str:
    return uuid.uuid4().hex


@pytest.fixture(scope="function")
def console() -> io.StringIO:
    return io.StringIO()
