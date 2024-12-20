from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol, TypeVar, runtime_checkable

_T_co = TypeVar("_T_co", covariant=True)
_T_contra = TypeVar("_T_contra", contravariant=True)


@dataclass
class Callback:
    func: Callable[..., Any]
    args: tuple[Any, ...] | None = None
    kwargs: dict[str, Any] | None = None

    @property
    def callable(self) -> bool:
        return callable(self.func)

    def get_args(self) -> tuple[Any, ...]:
        return self.args or ()

    def get_kwargs(self) -> dict[str, Any]:
        return self.kwargs or {}

    def call_with(self, *args: Any, **kwargs: Any):
        self.func(*args, **kwargs)

    def call(self):
        self.call_with(*self.get_args(), **self.get_kwargs())


@runtime_checkable
class SupportsWrite(Protocol[_T_contra]):
    """Protocol exposing an expected write method"""

    def write(self, s: _T_contra, /) -> object: ...


@runtime_checkable
class SupportsRead(Protocol[_T_co]):
    def read(self, length: int = ..., /) -> _T_co: ...


@runtime_checkable
class SupportsSeeking(Protocol):
    def seekable(self) -> bool: ...

    def seek(self, target: int, whence: int = 0) -> int: ...

    def tell(self) -> int: ...

    def truncate(self, pos: int) -> int: ...


@runtime_checkable
class SupportsSeekableRead(SupportsRead[_T_co], SupportsSeeking, Protocol): ...


@runtime_checkable
class SupportsSeekableWrite(SupportsWrite[_T_contra], SupportsSeeking, Protocol): ...
