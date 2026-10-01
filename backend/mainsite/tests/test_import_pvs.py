import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage, storages
from django.core.management import call_command

from election.models import ElectionCategory, ElectionDocument
from election.tests.factories import ElectionConfigFactory, ElectionFactory
from eml_import.tests.test_folder_pdf_file_handler import PDF_BYTES, write_pdf
from mainsite.models import RegionCategory
from region.tests.factories import RegionFactory


def gemeente(name: str = "Barneveld"):
    config = ElectionConfigFactory(identifier="TK2025", category=ElectionCategory.TK.value)
    election = ElectionFactory(election_config=config, subcategory="TK")
    return RegionFactory(
        election=election,
        region_category=RegionCategory.GEMEENTE,
        region_name=name,
        region_number="203",
    )


def use_pv_import(settings, backend, **options):
    settings.STORAGES = {
        **settings.STORAGES,
        "pv_import": {"BACKEND": backend, "OPTIONS": options},
    }


@pytest.mark.django_db
def test_import_pvs_reads_whatever_storage_is_configured(tmp_path, settings):
    gemeente()
    nested = tmp_path / "nested"
    nested.mkdir()
    write_pdf(nested, "TK2025_NA31-2_Barneveld.pdf")
    write_pdf(tmp_path, "readme.txt", b"not a pdf")
    use_pv_import(settings, "django.core.files.storage.FileSystemStorage", location=str(tmp_path))

    call_command("import_pvs")

    assert ElectionDocument.objects.get().size == len(PDF_BYTES)


@pytest.mark.django_db
def test_import_pvs_reads_an_object_storage_the_same_way(settings):
    barneveld = gemeente()
    use_pv_import(settings, "mainsite.tests.storage.InMemoryPresignStorage")
    source = storages["pv_import"]
    source.save("nested/TK2025_NA31-2_Barneveld.pdf", ContentFile(PDF_BYTES))
    source.save("readme.txt", ContentFile(b"not a pdf"))
    default_storage.save("elsewhere/TK2025_NA31-2_Barneveld.pdf", ContentFile(PDF_BYTES))

    call_command("import_pvs")

    document = ElectionDocument.objects.get()
    assert document.region == barneveld
    assert document.storage_key == "TK2025/TK2025_NA31-2_Barneveld.pdf"
    assert default_storage.open(document.storage_key).read() == PDF_BYTES
