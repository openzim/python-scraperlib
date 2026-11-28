from typing import NoReturn


def missing_extra(extra: str, error: ModuleNotFoundError) -> NoReturn:
    name = error.name or "an optional dependency"
    raise ImportError(
        f"Missing dependency '{name}' required by the '{extra}' extra. "
        f"Install it with `python -m pip install 'zimscraperlib[{extra}]'` "
        f"or `python -m pip install 'zimscraperlib[all]'`."
    ) from error
