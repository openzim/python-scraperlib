from zimscraperlib.typing import Callback


class GlobalCounter:
    count: int = 0


def update_counter() -> int:
    GlobalCounter.count += 1
    return GlobalCounter.count


def update_counter_args(bump: int) -> int:
    GlobalCounter.count += bump
    return GlobalCounter.count


def update_counter_kwargs(*, bump: int) -> int:
    GlobalCounter.count += bump
    return GlobalCounter.count


def update_counter_args_and_kwargs(bump: int, *, factor: int) -> int:
    GlobalCounter.count += bump * factor
    return GlobalCounter.count


def test_callback_init():
    assert Callback(update_counter)
    assert Callback(update_counter).callable
    GlobalCounter.count = 0
    assert GlobalCounter.count == 0
    Callback(update_counter_args, args=(1,)).call()
    assert GlobalCounter.count == 1
    Callback(update_counter_args, kwargs={"bump": 1}).call()
    assert GlobalCounter.count == 2
    Callback(update_counter_kwargs, kwargs={"bump": 1}).call()
    assert GlobalCounter.count == 3
    Callback(update_counter_args_and_kwargs, args=(1,), kwargs={"factor": 2}).call()
    assert GlobalCounter.count == 5
