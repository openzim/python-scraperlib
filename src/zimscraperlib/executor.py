import datetime
import queue
import threading
from collections.abc import Callable

from zimscraperlib import logger

_shutdown = False
# Lock that ensures that new workers are not created while the interpreter is
# shutting down. Must be held while mutating _threads_queues and _shutdown.
_global_shutdown_lock = threading.Lock()


def excepthook(args):  # pragma: no cover
    logger.error(f"UNHANDLED Exception in {args.thread.name}: {args.exc_type}")
    logger.exception(args.exc_value)


threading.excepthook = excepthook


class ScraperExecutor(queue.Queue):
    """Custom FIFO queue based Executor that's less generic than ThreadPoolExec one

    Providing more flexibility for the use cases we're interested about:
    - halt immediately (sort of) upon exception (if requested)
    - able to join() then restart later to accomodate successive steps

    See: https://github.com/python/cpython/blob/3.8/Lib/concurrent/futures/thread.py
    """

    def __init__(
        self,
        queue_size: int = 10,
        nb_workers: int = 1,
        executor_name: str = "executor",
        thread_deadline_sec: int = 60,
    ):
        super().__init__(queue_size)
        self.executor_name = executor_name
        self._shutdown_lock = threading.Lock()
        self.nb_workers = nb_workers
        self.exceptions = []
        self.thread_deadline_sec = thread_deadline_sec

    @property
    def exception(self):
        """Exception raises in any thread, if any"""
        try:
            return self.exceptions[0:1].pop()
        except IndexError:
            return None

    @property
    def alive(self):
        """whether it should continue running"""
        return not self._shutdown

    def submit(self, task: Callable, **kwargs):
        """Submit a callable and its kwargs for execution in one of the workers"""
        with self._shutdown_lock, _global_shutdown_lock:
            if not self.alive:
                raise RuntimeError("cannot submit task to dead executor")
            if self.no_more:
                raise RuntimeError(
                    "cannot submit task to a joined executor, restart it first"
                )
            if _shutdown:
                raise RuntimeError(  # pragma: no cover
                    "cannot submit task after interpreter shutdown"
                )

        while True:
            try:
                self.put((task, kwargs), block=True, timeout=3.0)
            except queue.Full:
                if self.no_more:
                    # rarely happens except if submit and join are done in different
                    # threads, but we need this to escape the while loop
                    break  # pragma: no cover
            else:
                break

    def start(self):
        """Enable executor, starting requested amount of workers

        Workers are started always, not provisioned dynamically"""
        logger.debug(f"Starting {self.executor_name} with {self.nb_workers} threads")

        self.drain()
        self._workers: set[threading.Thread] = set()
        self.no_more = False
        self._shutdown = False
        self.exceptions[:] = []

        for n in range(self.nb_workers):
            t = threading.Thread(target=self.worker, name=f"{self.executor_name}-{n}")
            t.daemon = True
            t.start()
            self._workers.add(t)

    def worker(self):
        while self.alive or self.no_more:
            try:
                func, kwargs = self.get(block=True, timeout=2.0)
            except queue.Empty:
                if self.no_more:
                    break
                continue
            except TypeError:  # pragma: no cover
                # received None from the queue. most likely shuting down
                return

            raises = kwargs.pop("raises") if "raises" in kwargs.keys() else False
            callback = kwargs.pop("callback") if "callback" in kwargs.keys() else None
            dont_release = kwargs.pop("dont_release", False)

            try:
                func(**kwargs)
            except Exception as exc:
                logger.error(f"Error processing {func} with {kwargs=}")
                logger.exception(exc)
                if raises:  # to cover when raises = False
                    self.exceptions.append(exc)
                    self.shutdown()
            finally:
                # user will manually release the queue for this task.
                # most likely in a libzim-written callback
                if not dont_release:
                    self.task_done()
                if callback:
                    callback.__call__()

    def drain(self):
        """Empty the queue without processing the tasks (tasks will be lost)"""
        while True:
            try:
                self.get_nowait()
            except queue.Empty:
                break

    def join(self):
        """Await completion of workers, requesting them to stop taking new task"""
        logger.debug(
            f"joining all threads for {self.executor_name}; threads have "
            f"{self.thread_deadline_sec}s to join before we give-up waiting for them"
        )
        self.no_more = True
        deadline = datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(
            seconds=self.thread_deadline_sec
        )
        alive_threads = list(filter(lambda t: t.is_alive(), self._workers))
        for t in filter(lambda t: t not in alive_threads, self._workers):
            logger.debug(f"Thread {t.name} is already dead. Skipping…")
        while (
            len(alive_threads) > 0 and datetime.datetime.now(tz=datetime.UTC) < deadline
        ):
            e = threading.Event()
            for t in alive_threads:
                t.join(0.1)  # just indicate to the thread that we want to stop
            e.wait(2)  # wait a bit more to let things cool down
            for t in filter(lambda t: not t.is_alive(), alive_threads):
                logger.debug(f"Thread {t.name} joined")
                alive_threads.remove(t)
        for t in alive_threads:
            logger.debug(f"Thread {t.name} never joined. Skipping…")
        logger.debug(f"join completed for {self.executor_name}")

    def shutdown(self, *, wait=True):
        """stop the executor, either somewhat immediately or awaiting completion"""
        logger.debug(f"shutting down {self.executor_name} with {wait=}")
        with self._shutdown_lock:
            self._shutdown = True

            # Drain all work items from the queue
            if not wait:
                self.drain()
        if wait:
            self.join()
