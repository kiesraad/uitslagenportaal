"""Classification of EML files by root Id, and OSV4-3 CSVs by header, into import order."""

from eml_import.tests.fakes import fake_osv43_csv
from eml_import.utils.file_handler import BaseFileHandler
from eml_import.utils.named_bytes_io import NamedBytesIO
from mainsite.utils.eml_type import CsvType, EmlType


class StubFileHandler(BaseFileHandler):
    """BaseFileHandler is abstract; classification does not depend on run()."""

    def run(self) -> tuple[int, bool]:
        return 0, False


def xml_with_id(document_id: str) -> NamedBytesIO:
    return NamedBytesIO(f"<EML Id='{document_id}'/>".encode(), f"{document_id}.eml.xml")


def test_classify_files_buckets_known_ids_in_import_order():
    handler = StubFileHandler()
    files = [
        xml_with_id("510d"),
        xml_with_id("110a"),
        xml_with_id("510c"),
        xml_with_id("510b"),
        xml_with_id("230b"),
        xml_with_id("110a"),
    ]

    classified = handler._classify_files(files)

    assert list(classified) == [
        EmlType.EML_110a,
        EmlType.EML_230b,
        EmlType.EML_510b,
        EmlType.EML_510c,
        EmlType.EML_510d,
        CsvType.CSV_OSV43,
    ]
    assert [f.getvalue() for f in classified[EmlType.EML_110a]] == [
        xml_with_id("110a").getvalue(),
        xml_with_id("110a").getvalue(),
    ]
    assert len(classified[EmlType.EML_230b]) == 1
    assert len(classified[EmlType.EML_510b]) == 1
    assert len(classified[EmlType.EML_510c]) == 1
    assert len(classified[EmlType.EML_510d]) == 1


def test_classify_files_ignores_unknown_root_ids():
    handler = StubFileHandler()
    files = [
        xml_with_id("110a"),
        xml_with_id("110b"),
        xml_with_id("510a"),
        xml_with_id("520"),
        xml_with_id("nope"),
        NamedBytesIO(b"<EML/>", "no-id.xml"),
    ]

    classified = handler._classify_files(files)

    assert sum(len(bucket) for bucket in classified.values()) == 1
    assert len(classified[EmlType.EML_110a]) == 1


def test_classify_files_buckets_osv43_csvs_by_header():
    handler = StubFileHandler()
    csv = fake_osv43_csv("Algemeen bestuur van het waterschap Aa en Maas 2023", "CSB", "Aa en Maas")

    classified = handler._classify_files([csv, xml_with_id("510d")])

    assert classified[CsvType.CSV_OSV43] == [csv]
    assert len(classified[EmlType.EML_510d]) == 1


def test_classify_files_ignores_csvs_without_osv43_header_and_other_extensions():
    handler = StubFileHandler()
    files = [
        NamedBytesIO('"Lijstnummer";"Aanduiding"\r\n"1";"Partij"'.encode(), "other.csv"),
        NamedBytesIO(b"<EML Id='110a'/>", "definitie.txt"),
    ]

    classified = handler._classify_files(files)

    assert sum(len(bucket) for bucket in classified.values()) == 0


def test_classify_files_leaves_csv_buffer_open_and_rewound():
    """The importer reads the same buffer again after classification."""
    handler = StubFileHandler()
    csv = fake_osv43_csv("Verkiezing X", "CSB", "Gebied X")

    handler._classify_files([csv])

    assert not csv.closed
    assert csv.tell() == 0
