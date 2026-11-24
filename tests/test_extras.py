import importlib.metadata
import re
import subprocess
import sys

import pytest

RUNTIME_EXTRA_DEPENDENCIES: dict[str, set[str]] = {
    "zim": {
        "libzim",
        "xxhash",
        "regex",
        "pymupdf-lite",
        "types-xxhash",
    },
    "image": {
        "pillow",
        "colorthief",
        "piexif",
        "optimize-images",
        "python-resize-image",
        "cairosvg",
    },
    "video": set(),
    "download": {"requests", "urllib3", "yt-dlp"},
    "filesystem": {"python-magic"},
    "html": {"beautifulsoup4", "lxml"},
    "rewriting": {
        "beautifulsoup4",
        "lxml",
        "idna",
        "tinycss2",
        "tree-sitter",
        "tree-sitter-javascript",
    },
    "i18n": {"babel", "iso639-lang"},
}

EXTRA_ROOTS: dict[str, set[str]] = {
    "zim": {"libzim", "regex", "pymupdf", "xxhash"},
    "image": {
        "PIL",
        "cairosvg",
        "colorthief",
        "piexif",
        "optimize_images",
        "resizeimage",
    },
    "video": set(),
    "download": {"requests", "urllib3", "yt_dlp"},
    "filesystem": {"magic"},
    "html": {"bs4", "lxml"},
    "rewriting": {
        "bs4",
        "lxml",
        "idna",
        "tinycss2",
        "tree_sitter",
        "tree_sitter_javascript",
    },
    "i18n": {"babel", "iso639"},
}

OPTIONAL_ROOTS: set[str] = set()
for roots in EXTRA_ROOTS.values():
    OPTIONAL_ROOTS.update(roots)

CHILD = """
import importlib
import sys

blocked = set(sys.argv[1].split(","))
module = sys.argv[2]

class Blocker:
    def find_spec(self, fullname, path=None, target=None):
        root = fullname.split(".", 1)[0]
        if root in blocked:
            raise ModuleNotFoundError(f"No module named {root!r}", name=root)
        return None

sys.meta_path.insert(0, Blocker())
try:
    importlib.import_module(module)
except ImportError as exc:
    print(str(exc))
else:
    raise SystemExit(0)
raise SystemExit(1)
"""


def _run_child(blocked: str, module: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", CHILD, blocked, module],
        capture_output=True,
        text=True,
        check=False,
    )


def _requirement_name(requirement: str) -> str:
    match = re.match(r"^([A-Za-z0-9_.-]+)", requirement)
    assert match is not None
    return match.group(1).lower()


def _names_for_extra(extra: str | None) -> set[str]:
    requirements = importlib.metadata.requires("zimscraperlib") or []
    return {
        _requirement_name(requirement)
        for requirement in requirements
        if (extra is None and "extra ==" not in requirement)
        or (extra is not None and f"extra == '{extra}'" in requirement)
    }


def test_runtime_extras_are_declared() -> None:
    declared = set(
        importlib.metadata.metadata("zimscraperlib").get_all("Provides-Extra") or []
    )
    assert set(RUNTIME_EXTRA_DEPENDENCIES) <= declared


def test_core_dependencies_are_minimal() -> None:
    assert _names_for_extra(None) == {"beartype"}


@pytest.mark.parametrize(("extra", "expected"), RUNTIME_EXTRA_DEPENDENCIES.items())
def test_extra_dependencies(extra: str, expected: set[str]) -> None:
    assert _names_for_extra(extra) == expected


def test_all_extra_covers_runtime_dependencies() -> None:
    expected: set[str] = set()
    for dependencies in RUNTIME_EXTRA_DEPENDENCIES.values():
        expected.update(dependencies)
    assert _names_for_extra("all") == expected


@pytest.mark.parametrize(
    ("extra", "module"),
    [
        ("download", "zimscraperlib.download"),
        ("filesystem", "zimscraperlib.filesystem"),
        ("html", "zimscraperlib.html"),
        ("i18n", "zimscraperlib.i18n"),
        ("image", "zimscraperlib.image"),
        ("rewriting", "zimscraperlib.rewriting.css"),
        ("zim", "zimscraperlib.zim"),
    ],
)
def test_missing_extra_message(extra: str, module: str) -> None:
    result = _run_child(",".join(sorted(EXTRA_ROOTS[extra])), module)
    assert result.returncode != 0
    assert any(f"'{root}'" in result.stdout for root in EXTRA_ROOTS[extra])
    assert f"zimscraperlib[{extra}]" in result.stdout
    assert "python -m pip install" in result.stdout


def test_core_import_needs_no_optional_dependencies() -> None:
    result = _run_child(",".join(sorted(OPTIONAL_ROOTS)), "zimscraperlib")
    assert result.returncode == 0
    assert result.stdout == ""


def test_video_import_needs_no_python_dependencies() -> None:
    result = _run_child(",".join(sorted(OPTIONAL_ROOTS)), "zimscraperlib.video")
    assert result.returncode == 0
    assert result.stdout == ""


def _remove_module(monkeypatch: pytest.MonkeyPatch, name: str) -> None:
    for key in tuple(sys.modules):
        if key == name or key.startswith(f"{name}."):
            monkeypatch.delitem(sys.modules, key, raising=False)


def _block_module(monkeypatch: pytest.MonkeyPatch, name: str) -> None:
    _remove_module(monkeypatch, name)
    monkeypatch.setitem(sys.modules, name, None)


def _import_without(monkeypatch: pytest.MonkeyPatch, extra: str, module: str) -> None:
    _remove_module(monkeypatch, module)
    for root in EXTRA_ROOTS[extra]:
        _block_module(monkeypatch, root)
    with pytest.raises(ImportError, match=rf"zimscraperlib\[{extra}\]"):
        importlib.import_module(module)


@pytest.mark.installed
@pytest.mark.parametrize(
    ("extra", "module"),
    [
        ("zim", "zimscraperlib.zim"),
        ("zim", "zimscraperlib.zim.archive"),
        ("zim", "zimscraperlib.zim.creator"),
        ("zim", "zimscraperlib.zim.dedup"),
        ("zim", "zimscraperlib.zim.indexing"),
        ("zim", "zimscraperlib.zim.items"),
        ("zim", "zimscraperlib.zim.metadata"),
        ("zim", "zimscraperlib.zim.providers"),
        ("image", "zimscraperlib.image.conversion"),
        ("image", "zimscraperlib.image.optimization"),
        ("image", "zimscraperlib.image.probing"),
        ("image", "zimscraperlib.image.transformation"),
        ("image", "zimscraperlib.image.utils"),
        ("rewriting", "zimscraperlib.rewriting.css"),
        ("rewriting", "zimscraperlib.rewriting.html"),
        ("rewriting", "zimscraperlib.rewriting.js_ast"),
        ("rewriting", "zimscraperlib.rewriting.url_rewriting"),
        ("download", "zimscraperlib.download"),
        ("filesystem", "zimscraperlib.filesystem"),
        ("html", "zimscraperlib.html"),
        ("i18n", "zimscraperlib.i18n"),
    ],
)
def test_missing_extra_error(
    monkeypatch: pytest.MonkeyPatch, extra: str, module: str
) -> None:
    _import_without(monkeypatch, extra, module)


@pytest.mark.installed
def test_url_provider_missing_download_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    importlib.import_module("zimscraperlib.download")
    _block_module(monkeypatch, "requests")

    from zimscraperlib.zim.providers import URLProvider  # noqa: PLC0415

    with pytest.raises(ImportError, match=r"zimscraperlib\[download\]"):
        URLProvider("https://example.com")


@pytest.mark.installed
def test_creator_lazy_default_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    _remove_module(monkeypatch, "zimscraperlib.zim.creator")
    creator = importlib.import_module("zimscraperlib.zim.creator")

    assert creator.DEFAULT_DEV_ZIM_METADATA.Name.value == "Test Name"
    assert creator.DEFAULT_DEV_ZIM_METADATA is creator.DEFAULT_DEV_ZIM_METADATA
    unknown = "UNKNOWN_ATTRIBUTE"
    with pytest.raises(AttributeError):
        getattr(creator, unknown)


def test_missing_extra_without_module_name() -> None:
    from zimscraperlib._extras import missing_extra  # noqa: PLC0415

    with pytest.raises(ImportError, match="an optional dependency"):
        missing_extra("test", ModuleNotFoundError())
