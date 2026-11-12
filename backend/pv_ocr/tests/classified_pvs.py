"""Classified PVs for the classifier and storage tests, built in code from a blank PDF."""

import io

import pypdfium2 as pdfium

from file_import.utils.named_bytes_io import NamedBytesIO
from pv_ocr.utils.pv_classifier import ClassificationResult, PvClassifier, PvElection, PvRegion, ResultMatch


def blank_pdf(width: int = 72) -> bytes:
    pdf = pdfium.PdfDocument.new()
    pdf.new_page(width, 72)
    buffer = io.BytesIO()
    pdf.save(buffer)
    pdf.close()
    return buffer.getvalue()


BLANK_PDF = blank_pdf()


def classified(model: str, election: PvElection, region: PvRegion, name: str = "pv.pdf") -> PvClassifier:
    pv = PvClassifier(NamedBytesIO(BLANK_PDF, name))
    pv.result = ClassificationResult(model, ResultMatch.CODE_TITLE, region=region, election=election)
    return pv


EDE_12 = PvRegion(code="228", name="Ede", stembureau="12")
