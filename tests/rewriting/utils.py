class ContentForTests:

    def __init__(
        self,
        input_: str | bytes,
        expected: str | bytes | None = None,
        article_url: str = "kiwix.org",
    ) -> None:
        self.input_ = input_
        self.expected = expected if expected is not None else input_
        self.article_url = article_url

    @property
    def input_str(self) -> str:
        if isinstance(self.input_, str):
            return self.input_
        raise ValueError("Input value is not a str.")

    @property
    def input_bytes(self) -> bytes:
        if isinstance(self.input_, bytes):
            return self.input_
        raise ValueError("Input value is not a bytes.")

    @property
    def expected_str(self) -> str:
        if isinstance(self.expected, str):
            return self.expected
        raise ValueError("Expected value is not a str.")

    @property
    def expected_bytes(self) -> bytes:
        if isinstance(self.expected, bytes):
            return self.expected
        raise ValueError("Expected value is not a bytes.")
