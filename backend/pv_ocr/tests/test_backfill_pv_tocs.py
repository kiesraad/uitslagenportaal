import re
from io import StringIO
from unittest.mock import call, patch

import pytest
from django.core.management import call_command

from election.models import ElectionDocument
from election.tests.factories import CertifiedElectionDocumentFactory, ElectionDocumentFactory
from pv_ocr.tasks import determine_document_toc
from pv_ocr.utils.toc_schema import TOC_VERSION, PageContent, TableOfContents, TocEntry

FileType = ElectionDocument.FileType


def outdated(document):
    """Store the document's TOC as an older version, bypassing the field that only writes the current one."""
    ElectionDocument.objects.filter(pk=document.pk).update(toc={"version": TOC_VERSION - 1, "entries": []})
    return document


@pytest.fixture
def documents():
    """The documents the backfill should pick up, among those it should leave alone."""
    missing = CertifiedElectionDocumentFactory(file_type=FileType.PDF_N10_1)
    old = outdated(CertifiedElectionDocumentFactory(file_type=FileType.PDF_NA14_1))
    CertifiedElectionDocumentFactory(file_type=FileType.PDF_O7, toc=TableOfContents([TocEntry(1, PageContent.COVER)]))
    CertifiedElectionDocumentFactory(file_type=FileType.PDF_NA31_2_B2)
    CertifiedElectionDocumentFactory(file_type=FileType.PDF_NA31_2, is_current=False)
    outdated(CertifiedElectionDocumentFactory(file_type=FileType.PDF_NA31_2_B2))
    ElectionDocumentFactory(file_type=FileType.EML_510B)
    return [missing.pk, old.pk]


@pytest.mark.django_db
@patch.object(determine_document_toc, "delay")
def test_queues_current_pvs_of_a_supported_model_without_a_current_toc(delay, documents):
    stdout = StringIO()

    call_command("backfill_pv_tocs", stdout=stdout)

    assert delay.call_args_list == [call(pk) for pk in documents]
    assert re.search(r"Queued the table of contents of 2 PV\(s\) in \d+\.\d s", stdout.getvalue())


@pytest.mark.django_db
@patch("pv_ocr.management.commands.backfill_pv_tocs.determine_document_toc")
def test_run_sync_runs_the_task_here(task, documents):
    call_command("backfill_pv_tocs", "--run-sync", stdout=StringIO())

    assert task.call_args_list == [call(pk) for pk in documents]
    task.delay.assert_not_called()


@pytest.mark.django_db
@patch("pv_ocr.management.commands.backfill_pv_tocs.determine_document_toc")
def test_an_interrupt_stops_with_what_was_done_and_no_traceback(task, documents):
    task.side_effect = [None, KeyboardInterrupt]
    stdout = StringIO()

    with pytest.raises(SystemExit) as exit_info:
        call_command("backfill_pv_tocs", "--run-sync", stdout=stdout)

    assert exit_info.value.code == 130
    assert re.search(r"Interrupted\. Determined the table of contents of 1 PV\(s\) in \d+\.\d s", stdout.getvalue())
