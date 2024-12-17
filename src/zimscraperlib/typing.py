from __future__ import annotations

from collections.abc import Callable
from typing import Any, NamedTuple


class Callback(NamedTuple):
    func: Callable
    args: tuple[Any, ...] | None = None
    kwargs: dict[str, Any] | None = None

    @property
    def callable(self) -> bool:
        return callable(self.func)

    def get_args(self) -> tuple[Any, ...]:
        return self.args or ()

    def get_kwargs(self) -> dict[str, Any]:
        return self.kwargs or {}

    def call_with(self, *args, **kwargs):
        self.func.__call__(*args, **kwargs)

    def call(self):
        self.call_with(*self.get_args(), **self.get_kwargs())
