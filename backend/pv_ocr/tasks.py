import logging
import time
from pathlib import Path

from botocore.exceptions import ConnectionError as S3ConnectionError
from django.core.files.storage import default_storage
from django.db import DatabaseError

from election.models import ElectionDocument
from file_import.utils.named_bytes_io import NamedBytesIO
from mainsite.celery import app
from pv_ocr.utils.pv_toc import PvDetermineTOC, pv_model
from pv_ocr.utils.toc_schema import PageContent

logger = logging.getLogger(__name__)

OCR_QUEUE = "ocr"
"""
Consumed by the OCR worker and, locally, by the `celery` compose service.
"""


@app.task(
    queue=OCR_QUEUE,
    ignore_result=True,
    autoretry_for=[DatabaseError, S3ConnectionError],
    retry_backoff=5,
    max_retries=2,
)
def determine_document_toc(document_id: int) -> None:
    """Determine and store the table of contents of a stored PV whose model the TOC knows; skip any other."""
    # Deferred, as a TOC of an older version cannot be read; it is replaced.
    document = ElectionDocument.all_objects.defer("toc").filter(pk=document_id).first()
    model = pv_model(document.file_type) if document else None
    if model is None:
        return
    with default_storage.open(document.storage_key) as stored:
        content = NamedBytesIO(stored.read(), document.storage_key)

    start = time.monotonic()
    document.toc = PvDetermineTOC(content, model=model).determine()
    elapsed = time.monotonic() - start
    document.save(update_fields=["toc", "updated_at"])
    unknown = sum(entry.content == PageContent.UNKNOWN for entry in document.toc.entries)
    logger.info(
        "Determined the table of contents of %s in %.1f s: %d page(s) classified, %d unknown",
        Path(document.storage_key).name,
        elapsed,
        len(document.toc.entries) - unknown,
        unknown,
    )
