import pathlib
from tempfile import TemporaryDirectory

from zimscraperlib.paths import path_from


def test_path_from_tmp_dir():
    tempdir = TemporaryDirectory()
    with path_from(tempdir) as tmp_dir:
        file = tmp_dir / "file.txt"
        file.touch()
        assert file.exists()
        assert pathlib.Path(tempdir.name).exists()

    assert not pathlib.Path(tempdir.name).exists()


def test_path_from_path():
    tempdir = TemporaryDirectory()
    tempdir_path = pathlib.Path(tempdir.name)
    with path_from(tempdir_path) as tmp_dir:
        file = tmp_dir / "file.txt"
        file.touch()
        assert file.exists()
        assert pathlib.Path(tempdir.name).exists()

    assert pathlib.Path(tempdir.name).exists()
    tempdir.cleanup()
    assert not pathlib.Path(tempdir.name).exists()


def test_path_from_str():
    tempdir = TemporaryDirectory()
    tempdir_path = pathlib.Path(tempdir.name)
    with path_from(str(tempdir_path)) as tmp_dir:
        file = tmp_dir / "file.txt"
        file.touch()
        assert file.exists()
        assert pathlib.Path(tempdir.name).exists()

    assert pathlib.Path(tempdir.name).exists()
    tempdir.cleanup()
    assert not pathlib.Path(tempdir.name).exists()
