import logging
from functools import partial
from time import sleep

import pytest

from zimscraperlib import logger
from zimscraperlib.executor import ScraperExecutor

logger.setLevel(logging.DEBUG)


class SomethingBadError(Exception):
    """Test exception"""

    pass


class Holder:
    value = 1


@pytest.mark.slow
def test_executor_ok():
    """Test basic standard case"""

    def increment(holder: Holder):
        holder.value += 1

    executor = ScraperExecutor(nb_workers=2)
    executor.start()
    test_value = Holder()
    for _ in range(99):
        if exception := executor.exception:
            raise exception
        executor.submit(increment, holder=test_value)
    executor.shutdown()
    assert test_value.value == 100


@pytest.mark.slow
def test_executor_with_one_failure():
    """Test case where the tasks are raising one failure and we want to stop asap"""

    def increment(holder: Holder):
        holder.value += 1
        if holder.value == 20:
            raise SomethingBadError()

    executor = ScraperExecutor(nb_workers=2)
    executor.start()
    test_value = Holder()
    with pytest.raises(SomethingBadError):
        for _ in range(99):
            if exception := executor.exception:
                raise exception
            executor.submit(increment, holder=test_value, raises=True)
    assert len(executor.exceptions) == 1
    executor.shutdown()
    # we have two workers, while one failed, the time it takes to raise the exception is
    # significant and the other worker is still processing items and we are still
    # enqueuing more items when the queue gets free, so we have many items processed
    # before the code stops
    assert test_value.value >= 21


@pytest.mark.slow
def test_executor_with_many_failure_raised():
    """Test case where the tasks are raising many failures and we want to stop asap"""

    def increment(holder: Holder):
        holder.value += 1
        if holder.value >= 20:
            raise SomethingBadError()

    executor = ScraperExecutor(nb_workers=3)
    executor.start()
    test_value = Holder()
    with pytest.raises(SomethingBadError):
        for _ in range(99):
            if exception := executor.exception:
                raise exception
            executor.submit(increment, holder=test_value, raises=True)
    executor.shutdown()
    # we have three workers, all failing once value is greater or equal to 20
    assert len(executor.exceptions) == 3
    assert test_value.value == 22


@pytest.mark.slow
def test_executor_slow():
    """Test case where the tasks are slow to run"""

    def increment(holder: Holder):
        holder.value += 1
        sleep(5)

    executor = ScraperExecutor(nb_workers=2)
    executor.start()
    test_value = Holder()
    for _ in range(19):
        if exception := executor.exception:
            raise exception
        executor.submit(increment, holder=test_value)
    executor.shutdown()
    assert test_value.value == 20


@pytest.mark.slow
def test_executor_stop_immediately():
    """Test case where we ask the executor to stop without waiting"""

    def increment(holder: Holder):
        holder.value += 1
        sleep(1)

    executor = ScraperExecutor(nb_workers=2)
    executor.start()
    test_value = Holder()
    for _ in range(5):
        if exception := executor.exception:
            raise exception
        executor.submit(increment, holder=test_value)
    executor.shutdown(wait=False)
    # we stopped asap, but 1 task might have been done in every worker
    assert test_value.value <= 3


@pytest.mark.slow
def test_executor_stop_once_done():
    """Test case where we ask the executor to stop once all tasks are done"""

    def increment(holder: Holder):
        holder.value += 1
        sleep(1)

    executor = ScraperExecutor(nb_workers=2)
    executor.start()
    test_value = Holder()
    for _ in range(4):
        if exception := executor.exception:
            raise exception
        executor.submit(increment, holder=test_value)
    executor.shutdown()
    assert test_value.value == 5  # we waited for queue to be processed


@pytest.mark.slow
def test_executor_stop_thread_not_joining():
    """Test case where threads take longer to join than the thread_deadline_sec"""

    def increment(holder: Holder):
        holder.value += 1
        sleep(5)

    executor = ScraperExecutor(nb_workers=2, thread_deadline_sec=1)
    executor.start()
    test_value = Holder()
    for _ in range(4):
        if exception := executor.exception:
            raise exception
        executor.submit(increment, holder=test_value)
    executor.shutdown()
    assert test_value.value >= 3  # threads finished their job before we stopped them


@pytest.mark.slow
def test_executor_already_shutdown():
    """Test case where we submit a task to an executor who is already shutdown"""

    def increment(holder: Holder):
        holder.value += 1

    executor = ScraperExecutor(nb_workers=2)
    executor.start()
    test_value = Holder()
    for _ in range(2):
        executor.submit(increment, holder=test_value)
    executor.shutdown()
    assert test_value.value == 3
    with pytest.raises(RuntimeError):
        executor.submit(increment, holder=test_value)


@pytest.mark.slow
def test_executor_already_joined():
    """Test case where we submit a task to an executor who is already joined"""

    def increment(holder: Holder):
        holder.value += 1

    executor = ScraperExecutor(nb_workers=2, queue_size=2)
    executor.start()
    test_value = Holder()
    for _ in range(2):
        executor.submit(increment, holder=test_value)
    executor.join()
    assert test_value.value == 3
    with pytest.raises(RuntimeError):
        executor.submit(increment, holder=test_value)


@pytest.mark.slow
def test_executor_join_and_restart():
    """Test case where we join an executor, and then restart it and submit tasks"""

    def increment(holder: Holder):
        holder.value += 1

    executor = ScraperExecutor(nb_workers=2, queue_size=2)
    executor.start()
    test_value = Holder()
    for _ in range(2):
        executor.submit(increment, holder=test_value)
    executor.join()
    assert test_value.value == 3
    executor.start()
    for _ in range(5):
        executor.submit(increment, holder=test_value)
    executor.join()
    assert test_value.value == 8


@pytest.mark.slow
def test_executor_callback_and_custom_release():
    """Test custom callback and custom release of the queue"""

    def increment(holder: Holder):
        holder.value += 1

    def callback(executor: ScraperExecutor, holder: Holder):
        holder.value += 1
        executor.task_done()

    executor = ScraperExecutor(nb_workers=2, queue_size=2)
    executor.start()
    test_value = Holder()
    for _ in range(2):
        executor.submit(
            increment,
            holder=test_value,
            callback=partial(callback, executor=executor, holder=test_value),
            dont_release=True,
        )
    executor.join()
    assert test_value.value == 5


@pytest.mark.slow
def test_executor_with_many_failure_not_raised():
    """Test case where we do not mind about exceptions during async processing"""

    def increment(holder: Holder):
        holder.value += 1
        if holder.value >= 20:
            raise SomethingBadError()

    executor = ScraperExecutor(nb_workers=3)
    executor.start()
    test_value = Holder()
    for _ in range(99):
        if exception := executor.exception:
            raise exception
        executor.submit(increment, holder=test_value)
    executor.shutdown()
    assert len(executor.exceptions) == 0
    assert test_value.value == 100


@pytest.mark.slow
def test_executor_slow_to_submit():
    """Check that executor does not care if tasks are submitted very slowly"""

    def increment(holder: Holder):
        holder.value += 1

    executor = ScraperExecutor(nb_workers=2)
    executor.start()
    test_value = Holder()
    for _ in range(2):
        sleep(5)
        if exception := executor.exception:
            raise exception
        executor.submit(increment, holder=test_value)
    executor.shutdown()
    assert test_value.value == 3
