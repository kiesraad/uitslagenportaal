from io import StringIO
from pathlib import Path
from unittest import mock

from django.core.management import call_command

from pv_scraper.utils.pv_classifier import ClassificationResult, PvClassifier, ResultMatch


def test_classify_pv_carries_on_after_a_failed_classification():
    stdout = StringIO()
    result = ClassificationResult("Na 31-2", ResultMatch.CODE_TITLE)
    with (
        mock.patch.object(PvClassifier, "__init__", return_value=None),
        mock.patch.object(PvClassifier, "classify", side_effect=[None, result]) as classify,
    ):
        call_command("classify_pv", Path("failed.pdf"), Path("next.pdf"), stdout=stdout)

    assert classify.call_count == 2
    assert "Classification failed" in stdout.getvalue()
    assert "model: Na 31-2" in stdout.getvalue()
