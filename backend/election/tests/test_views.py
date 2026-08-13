import datetime

import pytest
from django.http import Http404
from django.test import RequestFactory
from django.utils import timezone

from election.tests.factories import ElectionConfigFactory, ElectionDocumentFactory
from election.utils import VISIBILITY_MONTHS
from election.views import download_document


@pytest.fixture
def data_root(tmp_path, settings):
    settings.BASE_DIR = tmp_path
    root = tmp_path / ".data"
    root.mkdir()
    return root


@pytest.fixture
def expired_election():
    """An election old enough to be past the visibility window, like GR2026."""
    # 31 days per month keeps this comfortably past the cutoff whatever the
    # calendar does with short months.
    started = timezone.now() - datetime.timedelta(days=31 * VISIBILITY_MONTHS + 1)
    return ElectionConfigFactory(identifier="GR2026", label="Gemeenteraad 2026", date=started)


@pytest.fixture
def current_election():
    return ElectionConfigFactory(identifier="AB2023", label="Waterschappen 2023")


@pytest.mark.django_db
def test_expired_election_is_left_out_of_the_config_list(client, expired_election, current_election):
    response = client.get("/api/election_configs/")

    assert response.status_code == 200
    assert [item["slug"] for item in response.json()] == [current_election.slug]


@pytest.mark.django_db
def test_expired_election_detail_returns_404(client, expired_election):
    # A direct link to a hidden election has to fail rather than render an
    # otherwise empty page.
    response = client.get(f"/api/election_configs/{expired_election.slug}/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_current_election_detail_is_still_reachable(client, current_election):
    response = client.get(f"/api/election_configs/{current_election.slug}/")

    assert response.status_code == 200
    assert response.json()["slug"] == current_election.slug


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
