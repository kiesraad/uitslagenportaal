import pytest
from django.http import Http404
from django.test import RequestFactory

from election.tests.factories import ElectionDocumentFactory
from election.views import download_document


@pytest.fixture
def data_root(tmp_path, settings):
    settings.BASE_DIR = tmp_path
    root = tmp_path / ".data"
    root.mkdir()
    return root


@pytest.mark.django_db
def test_download_document_returns_file_for_valid_storage_key(data_root):
    (data_root / "document.xml").write_bytes(b"<eml>ok</eml>")
    document = ElectionDocumentFactory(storage_key="document.xml", content_type="application/xml", size=13)

    response = download_document(RequestFactory().get("/"), document.pk)

    assert response.status_code == 200
    assert b"".join(response.streaming_content) == b"<eml>ok</eml>"


@pytest.mark.django_db
def test_download_document_rejects_path_traversal(data_root):
    secret = data_root.parent / "secret.txt"
    secret.write_bytes(b"top secret")
    document = ElectionDocumentFactory(storage_key="../secret.txt", content_type="text/plain", size=10)

    # download_document is a plain function view, so calling it directly
    # (bypassing Django's outer exception-to-response handler) means Http404
    # surfaces as a raised exception rather than a 404 response.
    with pytest.raises(Http404):
        download_document(RequestFactory().get("/"), document.pk)


@pytest.mark.django_db
def test_download_document_returns_404_for_missing_document(data_root):
    with pytest.raises(Http404):
        download_document(RequestFactory().get("/"), 999999)
