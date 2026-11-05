import re

from django.core.files.storage import storages

from mainsite.models import RegionCategory
from pv_ocr.utils.pv_classifier import PvClassificationException, PvClassifier
from pv_scraper.models import ScrapeSource

STORAGE_ENTRY = "pv_import"
"""
The storage config entry from which the PVs are imported
"""

# The source kind whose name is the authority of an election type, when the header doesn't name it.
AUTHORITY_SOURCE_KINDS = {"PS": RegionCategory.PROVINCIE, "AB": RegionCategory.WATERSCHAP}
# What such a source's name may put before the authority: "Provincie Drenthe", "Hoogheemraadschap van Delfland".
SOURCE_NAME_PREFIX_RE = re.compile(r"^(?:provincie|waterschap|hoogheemraadschap|wetterskip)\s+(?:van\s+)?", re.I)


def save_to_storage(classifier: PvClassifier, source: ScrapeSource, folder: str) -> str:
    """Store the PV with its metadata under its name in a folder, replacing a file of that name, and return the
    storage key.

    A PV found on a gemeente's website must be about that gemeente, unless its region is a CSB or a kieskring; the
    source then also gives the gemeente's name, and that of a waterschap or province the CSB.
    """
    if classifier.result is None:
        raise PvClassificationException("Cannot save file: not classified")

    # What the source tells about the PV overrides what was read from it; empty keeps what was read.
    election, region = classifier.result.election, classifier.result.region
    csb = region_code = region_name = ""

    # A gemeente's website gives the gemeente, which the PV must name too: as its region, by code or name, or as
    # the gemeenteraad in a GR header. Each of the two it names must match.
    if source.kind == RegionCategory.GEMEENTE and not (classifier.is_csb_pv() or classifier.is_kieskring_pv()):
        region_code, region_name = source.code.removeprefix("gm"), source.name
        gemeenteraad = election.authority if election.id.startswith("GR") else ""
        if not (region.code or region.name or gemeenteraad):
            raise PvClassificationException("Cannot save file: PV does not name its gemeente")
        if (region.code or region.name) and region.code != region_code:
            if not classifier.authority_matches(source.name, region.name):
                raise PvClassificationException(f"Cannot save file: PV is not from {source}")
        if gemeenteraad and not classifier.authority_matches(source.name, gemeenteraad):
            raise PvClassificationException(f"Cannot save file: PV is from {gemeenteraad}")

    # A province's or waterschap's website gives the CSB of a PS or AB election, spelled as in AUTHORITIES.
    elif source.kind == AUTHORITY_SOURCE_KINDS.get(election.id[:2]):
        csb = classifier.known_authority(election.id[:2], SOURCE_NAME_PREFIX_RE.sub("", source.name))

    # Name the PV and add what it is to its PDF metadata.
    pv = classifier.identity(csb, region_code, region_name)
    key = f"{folder}/{classifier.storage_name(pv)}"
    content = classifier.add_metadata_to_pv(pv)

    # Replace a file of the same name, which storage would otherwise keep, saving this one under a suffixed name.
    storage = storages[STORAGE_ENTRY]
    if storage.exists(key):
        storage.delete(key)
    return storage.save(key, content)
