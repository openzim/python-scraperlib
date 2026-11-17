"""Import-graph boundaries between the library's families.

Importing `zim` or `inputs` must not require yt-dlp, beautifulsoup4 or lxml,
so those are hidden from a child interpreter and the module imported anyway.
"""

import subprocess
import sys

SCRIPT = """
import sys

BLOCKED = {blocked!r}


class Blocker:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in BLOCKED:
            raise ModuleNotFoundError(f"No module named {{fullname!r}}")
        return None


sys.meta_path.insert(0, Blocker())
import {module}
"""


def import_with_blocked(
    module: str, blocked: set[str]
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", SCRIPT.format(module=module, blocked=blocked)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_zim_import_needs_no_yt_dlp():
    result = import_with_blocked("zimscraperlib.zim", {"yt_dlp"})
    assert result.returncode == 0, result.stderr


def test_zim_import_needs_no_bs4_or_lxml():
    result = import_with_blocked("zimscraperlib.zim", {"bs4", "lxml"})
    assert result.returncode == 0, result.stderr


def test_inputs_import_needs_no_yt_dlp():
    result = import_with_blocked("zimscraperlib.inputs", {"yt_dlp"})
    assert result.returncode == 0, result.stderr


def test_download_does_need_yt_dlp():
    """The blocker works, so the tests above are not vacuous"""
    result = import_with_blocked("zimscraperlib.download", {"yt_dlp"})
    assert result.returncode != 0
    assert "No module named 'yt_dlp'" in result.stderr
