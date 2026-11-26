from unittest.mock import patch

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage, storages
from django.core.management import call_command

from election.models import ElectionDocument
from file_import.tests.pdf_files import PDF_BYTES, barneveld, write_pdf
from pv_ocr.tasks import determine_document_toc


def use_pv_import(settings, backend, **options):
    settings.STORAGES = {
        **settings.STORAGES,
        "pv_import": {"BACKEND": backend, "OPTIONS": options},
    }


@pytest.mark.django_db
@patch.object(determine_document_toc, "delay")
def test_import_pvs_reads_whatever_storage_is_configured(delay, tmp_path, settings):
    barneveld()
    use_pv_import(settings, "django.core.files.storage.FileSystemStorage", location=str(tmp_path))
    key = write_pdf("nested/TK2025_Nederland_NA31-2_Barneveld.pdf")
    storages["pv_import"].save("readme.txt", ContentFile(b"not a pdf"))

    call_command("import_pvs")

    assert ElectionDocument.objects.get().size == len(PDF_BYTES)
    assert not storages["pv_import"].exists(key)


@pytest.mark.django_db
@patch.object(determine_document_toc, "delay")
def test_import_pvs_reads_an_object_storage_the_same_way(delay, settings):
    region = barneveld()
    use_pv_import(settings, "mainsite.tests.storage.InMemoryPresignStorage")
    key = write_pdf("nested/TK2025_Nederland_NA31-2_Barneveld.pdf")
    storages["pv_import"].save("readme.txt", ContentFile(b"not a pdf"))
    default_storage.save("elsewhere/TK2025_Nederland_NA31-2_Barneveld.pdf", ContentFile(PDF_BYTES))

    call_command("import_pvs")

    document = ElectionDocument.objects.get()
    delay.assert_called_once_with(document.pk)
    assert document.region == region
    assert document.storage_key == "TK2025/pvs/TK2025_Nederland_NA31-2_Barneveld.pdf"
    assert default_storage.open(document.storage_key).read() == PDF_BYTES
    assert not storages["pv_import"].exists(key)
