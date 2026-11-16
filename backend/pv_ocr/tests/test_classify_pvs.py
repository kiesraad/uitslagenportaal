from io import StringIO
from unittest.mock import patch

from django.core.management import call_command

from pv_ocr.management.commands.classify_pvs import classify_timed
from pv_ocr.tests.classified_pvs import BLANK_PDF, blank_pdf
from pv_ocr.utils.pv_classifier import ClassificationResult, PvClassificationException, PvClassifier, ResultMatch

TOO_LARGE = "Page is larger than A3, so not a PV"


def test_classify_timed_returns_the_classification_exception_as_the_error(tmp_path):
    path = tmp_path / "poster.pdf"
    path.write_bytes(blank_pdf(width=2000))

    result, name, error, seconds = classify_timed(path)

    assert (result, name, error) == (None, "", TOO_LARGE)
    assert seconds >= 0


def test_classify_pvs_prints_an_error_row_for_a_page_larger_than_a3(tmp_path):
    path = tmp_path / "poster.pdf"
    path.write_bytes(blank_pdf(width=2000))
    out = StringIO()

    call_command("classify_pvs", path, stdout=out)

    error_rows = [line for line in out.getvalue().splitlines() if line.startswith("error")]
    assert len(error_rows) == 1
    assert error_rows[0].endswith(f"{path}  {TOO_LARGE}")


def test_classify_timed_keeps_the_result_when_storage_name_raises(tmp_path):
    path = tmp_path / "pv.pdf"
    path.write_bytes(BLANK_PDF)
    classified = ClassificationResult("N 10-2", ResultMatch.CODE_TITLE)

    with (
        patch.object(PvClassifier, "classify", return_value=classified),
        patch.object(PvClassifier, "storage_name", side_effect=PvClassificationException("region not known")),
    ):
        result, name, error, _ = classify_timed(path)

    assert (result, name, error) == (classified, "", None)
