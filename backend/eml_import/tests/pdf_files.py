from django.core.files.base import ContentFile
from django.core.files.storage import Storage, storages

from election.models import ElectionCategory
from election.tests.factories import ElectionConfigFactory, ElectionFactory
from mainsite.models import RegionCategory
from region.models import Region
from region.tests.factories import RegionFactory


def one_page_pdf(mark: bytes = b"a", meta: dict[str, str] | None = None) -> bytes:
    """A one-page PDF pdfium can open. `mark` only changes the bytes."""
    info = trailer = b""
    if meta:
        entries = b"".join(b"/" + key.encode() + b"(" + value.encode() + b")" for key, value in meta.items())
        info = b"4 0 obj<<" + entries + b">>endobj\n"
        trailer = b"/Info 4 0 R"
    return (
        b"%PDF-1.4\n%"
        + mark
        + b"\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        + b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
        + b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\n"
        + info
        + b"trailer<</Root 1 0 R"
        + trailer
        + b">>\n%%EOF\n"
    )


def pv_pdf(mark: bytes = b"a", **pv: str) -> bytes:
    meta = {"PvElection": "TK2025", "PvModel": "NA31-2", "PvRegionName": "Barneveld", **pv}
    return one_page_pdf(mark, {key: value for key, value in meta.items() if value})


PDF_BYTES = pv_pdf()


def write_pdf(name: str, content: bytes = PDF_BYTES, storage: Storage | None = None) -> str:
    storage = storage or storages["pv_import"]
    if storage.exists(name):
        storage.delete(name)
    return storage.save(name, ContentFile(content))


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
