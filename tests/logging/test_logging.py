import io
import logging
import pathlib

from zimscraperlib.logging import getLogger, nicer_args_join


def assert_message_console(
    logger: logging.Logger,
    console: io.StringIO,
    level: str,
    expected: bool,  # noqa: FBT001 (simpler for tests reading, used only in tests)
):
    msg = f"a {level} message"
    getattr(logger, level)(msg)
    if expected:
        assert msg in console.getvalue()
    else:
        assert msg not in console.getvalue()


def assert_message_file(
    logger: logging.Logger,
    fpath: pathlib.Path,
    level: str,
    expected: bool,  # noqa: FBT001 (simpler for tests reading, used only in tests)
):
    msg = f"a {level} message"
    getattr(logger, level)(msg)
    with open(fpath) as file:
        file.seek(0)
        if expected:
            assert msg in file.read()
        else:
            assert msg not in file.read()


def test_args_join():
    args = ["zimwriterfs", "--title", "some value"]
    nicer = nicer_args_join(args)
    assert nicer.startswith(args[0])
    assert f" {args[1]}" in nicer
    assert f' {args[1]} "{args[2]}"' in nicer


def test_default(random_id: str):
    logger = getLogger(name=random_id)
    logger.debug("a debug")
    logger.info("an info")
    logger.warning("a warning")
    logger.error("an error")
    logger.critical("a critical")


def test_debug_level(random_id: str, console: io.StringIO):
    logger = getLogger(name=random_id, console=console, level=logging.DEBUG)
    assert_message_console(logger, console, "debug", True)


def test_info_level(random_id: str, console: io.StringIO):
    logger = getLogger(name=random_id, console=console, level=logging.INFO)
    assert_message_console(logger, console, "debug", False)
    assert_message_console(logger, console, "info", True)


def test_warning_level(random_id: str, console: io.StringIO):
    logger = getLogger(name=random_id, console=console, level=logging.WARNING)
    assert_message_console(logger, console, "debug", False)
    assert_message_console(logger, console, "info", False)
    assert_message_console(logger, console, "warning", True)


def test_error_level(random_id: str, console: io.StringIO):
    logger = getLogger(name=random_id, console=console, level=logging.ERROR)
    assert_message_console(logger, console, "debug", False)
    assert_message_console(logger, console, "info", False)
    assert_message_console(logger, console, "warning", False)
    assert_message_console(logger, console, "error", True)


def test_critical_level(random_id: str, console: io.StringIO):
    logger = getLogger(name=random_id, console=console, level=logging.CRITICAL)
    assert_message_console(logger, console, "debug", False)
    assert_message_console(logger, console, "info", False)
    assert_message_console(logger, console, "warning", False)
    assert_message_console(logger, console, "error", False)
    assert_message_console(logger, console, "critical", True)


def test_format():
    # assert is_in_log(message, console)
    # "[%(asctime)s] %(levelname)s:%(message)s"
    pass


def test_file_logger(random_id: str, tmp_path: pathlib.Path):
    log_file = tmp_path / "test.log"
    logger = getLogger(name=random_id, file=log_file)
    logger.debug("a debug")
    logger.info("an info")
    logger.warning("a warning")
    logger.error("an error")
    logger.critical("a critical")


def test_debug_level_file(random_id: str, tmp_path: pathlib.Path):
    log_file = tmp_path / "test.log"
    logger = getLogger(name=random_id, file=log_file, file_level=logging.DEBUG)
    assert_message_file(logger, log_file, "debug", True)


def test_info_level_file(random_id: str, tmp_path: pathlib.Path):
    log_file = tmp_path / "test.log"
    logger = getLogger(name=random_id, file=log_file, file_level=logging.INFO)
    assert_message_file(logger, log_file, "debug", False)
    assert_message_file(logger, log_file, "info", True)


def test_warning_level_file(random_id: str, tmp_path: pathlib.Path):
    log_file = tmp_path / "test.log"
    logger = getLogger(name=random_id, file=log_file, file_level=logging.WARNING)
    assert_message_file(logger, log_file, "debug", False)
    assert_message_file(logger, log_file, "info", False)
    assert_message_file(logger, log_file, "warning", True)


def test_error_level_file(random_id: str, tmp_path: pathlib.Path):
    log_file = tmp_path / "test.log"
    logger = getLogger(name=random_id, file=log_file, file_level=logging.ERROR)
    assert_message_file(logger, log_file, "debug", False)
    assert_message_file(logger, log_file, "info", False)
    assert_message_file(logger, log_file, "warning", False)
    assert_message_file(logger, log_file, "error", True)


def test_critical_level_file(random_id: str, tmp_path: pathlib.Path):
    log_file = tmp_path / "test.log"
    logger = getLogger(name=random_id, file=log_file, file_level=logging.CRITICAL)
    assert_message_file(logger, log_file, "debug", False)
    assert_message_file(logger, log_file, "info", False)
    assert_message_file(logger, log_file, "warning", False)
    assert_message_file(logger, log_file, "error", False)
    assert_message_file(logger, log_file, "critical", True)


def test_level_fallback(random_id: str, tmp_path: pathlib.Path):
    log_file = tmp_path / "test.log"
    logger = getLogger(name=random_id, file=log_file, level=logging.CRITICAL)
    assert_message_file(logger, log_file, "debug", False)
    assert_message_file(logger, log_file, "info", False)
    assert_message_file(logger, log_file, "warning", False)
    assert_message_file(logger, log_file, "error", False)
    assert_message_file(logger, log_file, "critical", True)


def test_no_output(random_id: str):
    logger = getLogger(name=random_id, console=None, file=None)
    logger.error("error")


def test_additional_deps(random_id: str):
    assert logging.getLogger("something").level == logging.NOTSET
    getLogger(name=random_id, additional_deps=["something"], console=None, file=None)
    assert logging.getLogger("something").level == logging.WARNING
