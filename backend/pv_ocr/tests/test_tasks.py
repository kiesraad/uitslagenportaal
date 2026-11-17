import logging
import re
from unittest.mock import patch

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from election.models import ElectionDocument
from election.tests.factories import CertifiedElectionDocumentFactory
from pv_ocr import tasks
from pv_ocr.tasks import determine_document_toc
from pv_ocr.utils.toc_schema import TOC_VERSION, PageContent, TableOfContents, TocEntry

TOC = TableOfContents(
    [TocEntry(1, PageContent.COVER), TocEntry(2, PageContent.VOTES_CAST), TocEntry(3, PageContent.UNKNOWN)]
)


@pytest.mark.django_db
@patch.object(tasks, "PvDetermineTOC", autospec=True)
def test_determine_document_toc_stores_the_toc_of_the_pv(determine_toc, caplog):
    caplog.set_level(logging.INFO)
    determine_toc.return_value.determine.return_value = TOC
    document = CertifiedElectionDocumentFactory(
        storage_key="TK2025/pv/b1.pdf", file_type=ElectionDocument.FileType.PDF_NA31_2_B1
    )
    default_storage.save(document.storage_key, ContentFile(b"%PDF-1.7"))

    determine_document_toc(document.pk)

    [content] = determine_toc.call_args.args
    assert content.getvalue() == b"%PDF-1.7"
    assert determine_toc.call_args.kwargs == {"model": "Na 31-2 Bijlage 1"}
    document.refresh_from_db()
    assert document.toc == TOC
    assert re.fullmatch(
        r"Determined the table of contents of b1\.pdf in \d+\.\d s: 2 page\(s\) classified, 1 unknown",
        caplog.messages[-1],
    )


@pytest.mark.django_db
@patch.object(tasks, "PvDetermineTOC", autospec=True)
def test_determine_document_toc_replaces_a_toc_of_an_older_version(determine_toc):
    determine_toc.return_value.determine.return_value = TOC
    document = CertifiedElectionDocumentFactory(file_type=ElectionDocument.FileType.PDF_N10_1)
    ElectionDocument.objects.filter(pk=document.pk).update(toc={"version": TOC_VERSION - 1, "entries": []})
    default_storage.save(document.storage_key, ContentFile(b"%PDF-1.7"))

    determine_document_toc(document.pk)

    document.refresh_from_db()
    assert document.toc == TOC


@pytest.mark.django_db
@patch.object(tasks, "PvDetermineTOC", autospec=True)
def test_determine_document_toc_skips_a_file_type_without_a_model(determine_toc):
    document = CertifiedElectionDocumentFactory(file_type=ElectionDocument.FileType.PDF_NA31_2_B2)

    determine_document_toc(document.pk)

    determine_toc.assert_not_called()
    document.refresh_from_db()
    assert document.toc is None


@pytest.mark.django_db
@patch.object(tasks, "PvDetermineTOC", autospec=True)
def test_determine_document_toc_ignores_a_deleted_document(determine_toc):
    determine_document_toc(12345)

    determine_toc.assert_not_called()
