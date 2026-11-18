import pytest

from election.models import ElectionDocument
from election.tests.factories import CertifiedElectionDocumentFactory
from pv_ocr.utils.toc_schema import PageContent, TableOfContents, TocEntry

TOC = TableOfContents(
    [
        TocEntry(1, PageContent.COVER),
        TocEntry(2, PageContent.CANDIDATE_VOTES, 4),
        TocEntry(3, PageContent.CANDIDATE_VOTES_CONTINUED, 4, list_number_inferred=True),
    ]
)


@pytest.mark.django_db
def test_a_stored_toc_reads_back_as_a_table_of_contents():
    document = CertifiedElectionDocumentFactory(toc=TOC)

    document.refresh_from_db()

    assert document.toc == TOC


@pytest.mark.django_db
def test_a_document_without_toc_reads_back_as_none():
    document = CertifiedElectionDocumentFactory()

    document.refresh_from_db()

    assert document.toc is None


@pytest.mark.django_db
def test_toc_can_be_filtered_on_and_selected():
    with_toc = CertifiedElectionDocumentFactory(toc=TOC)
    without_toc = CertifiedElectionDocumentFactory()

    assert list(ElectionDocument.objects.filter(toc__isnull=True)) == [without_toc]
    assert list(ElectionDocument.objects.filter(toc__entries__1__list_number=4)) == [with_toc]
    assert list(ElectionDocument.objects.filter(pk=with_toc.pk).values_list("toc", flat=True)) == [TOC]
