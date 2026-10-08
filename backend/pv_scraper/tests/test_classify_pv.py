from io import StringIO
from unittest import mock

import pytest
from django.core.management import CommandError, call_command

from pv_scraper.utils.pv_classifier import ClassificationResult, PvClassifier, ResultMatch


def test_classify_pv_carries_on_after_a_failed_classification(tmp_path):
    paths = [tmp_path / "failed.pdf", tmp_path / "next.pdf"]
    for path in paths:
        path.write_bytes(b"%PDF")
    stdout = StringIO()
    result = ClassificationResult("Na 31-2", ResultMatch.CODE_TITLE)
    with (
        mock.patch.object(PvClassifier, "__init__", return_value=None),
        mock.patch.object(PvClassifier, "classify", side_effect=[None, result]) as classify,
    ):
        call_command("classify_pv", *paths, stdout=stdout)

    assert classify.call_count == 2
    assert "Classification failed" in stdout.getvalue()
    assert "model: Na 31-2" in stdout.getvalue()


@pytest.mark.parametrize("name", ["missing.pdf", "folder", "pv.txt"])
def test_classify_pv_takes_only_pdf_files(tmp_path, name):
    (tmp_path / "folder").mkdir()
    (tmp_path / "pv.txt").write_bytes(b"")

    with pytest.raises(CommandError, match="is not a PDF file"):
        call_command("classify_pv", tmp_path / name)
