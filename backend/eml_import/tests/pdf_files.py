from io import BytesIO

from django.core.files.base import ContentFile
from django.core.files.storage import Storage, storages
from pypdf import PdfWriter

from election.models import ElectionCategory
from election.tests.factories import ElectionConfigFactory, ElectionFactory
from eml_import.utils.pdf_file_handler import DEFAULT_PV_DIRECTORY
from mainsite.models import RegionCategory
from region.models import Region
from region.tests.factories import RegionFactory


def one_page_pdf(mark: bytes = b"a", meta: dict[str, str] | None = None) -> bytes:
    """A one-page PDF pdfium can open. `mark` only changes the bytes."""
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.add_metadata({"/Mark": mark.decode(), **{f"/{key}": value for key, value in (meta or {}).items()}})
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def pv_pdf(mark: bytes = b"a", **pv: str) -> bytes:
    meta = {"PvElection": "TK2025", "PvModel": "NA31-2", "PvRegionName": "Barneveld", **pv}
    return one_page_pdf(mark, {key: value for key, value in meta.items() if value})


PDF_BYTES = pv_pdf()


def write_pdf(
    name: str, content: bytes = PDF_BYTES, storage: Storage | None = None, directory: str = DEFAULT_PV_DIRECTORY
) -> str:
    """Store a PDF in the import queue and return its key."""
    storage = storage or storages["pv_import"]
    key = f"{directory}/{name}"
    if storage.exists(key):
        storage.delete(key)
    return storage.save(key, ContentFile(content))


def barneveld() -> Region:
    """Gemeente Barneveld for TK2025."""
    config = ElectionConfigFactory(identifier="TK2025", category=ElectionCategory.TK.value)
    election = ElectionFactory(election_config=config, subcategory="TK")
    # The STAAT region of a TK election definition carries a name but no number.
    staat = RegionFactory(
        election=election,
        region_category=RegionCategory.STAAT,
        region_name="Nederland",
        region_number=None,
    )
    return RegionFactory(
        election=election,
        parent=staat,
        csb=staat,
        region_category=RegionCategory.GEMEENTE,
        region_name="Barneveld",
        region_number="203",
    )
