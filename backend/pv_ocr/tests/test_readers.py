import subprocess
import sys

import pytest

from pv_ocr import readers
from pv_ocr.readers import NumberReader, Reading, get_reader, to_digits


class StubReader(NumberReader):
    def __init__(self, **options):
        self.options = options

    def read(self, images):
        return [Reading("1", 1.0) for _ in images]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("123", "123"),
        ("IlOoz", "11002"),
        ("12.345,6-", "123456"),
        ("abc", ""),
        ("", ""),
    ],
)
def test_to_digits(text, expected):
    assert to_digits(text) == expected


def test_get_reader_unknown_name_lists_known_readers():
    with pytest.raises(ValueError, match="Unknown reader 'nope'; known are trocr"):
        get_reader("nope")


def test_get_reader_builds_registered_reader_with_options(monkeypatch):
    monkeypatch.setitem(readers.READERS, "stub", f"{__name__}.StubReader")

    reader = get_reader("stub", checkpoint="x", batch_size=2)

    assert isinstance(reader, StubReader)
    assert reader.options == {"checkpoint": "x", "batch_size": 2}


def test_importing_readers_does_not_import_torch():
    if "torch" in sys.modules:
        pytest.skip("torch is already loaded by another test")
    code = "import sys, pv_ocr.readers; sys.exit('torch' in sys.modules)"

    assert subprocess.run([sys.executable, "-c", code], check=False).returncode == 0
