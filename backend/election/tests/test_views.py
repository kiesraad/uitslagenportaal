import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import Http404
from django.test import RequestFactory

from election.tests.factories import ElectionDocumentFactory
from election.views import download_document


@pytest.mark.django_db
def test_download_document_returns_file_for_valid_storage_key():
    default_storage.save("document.xml", ContentFile(b"<eml>ok</eml>"))
    document = ElectionDocumentFactory(storage_key="document.xml", content_type="application/xml", size=13)

    response = download_document(RequestFactory().get("/"), document.pk)

    assert response.status_code == 302
    assert response.url == default_storage.url("document.xml")


@pytest.mark.django_db
def test_download_document_returns_404_for_missing_document():
    with pytest.raises(Http404):
        download_document(RequestFactory().get("/"), 999999)
