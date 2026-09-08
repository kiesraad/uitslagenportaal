"""Classification of EML files by root Id into import order."""

from io import BytesIO

from eml_import.utils.file_handler import BaseFileHandler
from mainsite.utils.eml_type import EmlType


def xml_with_id(document_id: str) -> BytesIO:
    return BytesIO(f"<EML Id='{document_id}'/>".encode())


def test_classify_files_buckets_known_ids_in_import_order():
    handler = BaseFileHandler()
    files = [
        xml_with_id("510d"),
        xml_with_id("110a"),
        xml_with_id("510b"),
        xml_with_id("230b"),
        xml_with_id("110a"),
    ]

    classified = handler._classify_files(files)

    assert list(classified) == [
        EmlType.EML_110a,
        EmlType.EML_230b,
        EmlType.EML_510b,
        EmlType.EML_510d,
    ]
    assert [f.getvalue() for f in classified[EmlType.EML_110a]] == [
        xml_with_id("110a").getvalue(),
        xml_with_id("110a").getvalue(),
    ]
    assert len(classified[EmlType.EML_230b]) == 1
    assert len(classified[EmlType.EML_510b]) == 1
    assert len(classified[EmlType.EML_510d]) == 1


def test_classify_files_ignores_unknown_root_ids():
    handler = BaseFileHandler()
    files = [
        xml_with_id("110a"),
        xml_with_id("110b"),
        xml_with_id("510a"),
        xml_with_id("510c"),
        xml_with_id("520"),
        xml_with_id("nope"),
        BytesIO(b"<EML/>"),
    ]

    classified = handler._classify_files(files)

    assert sum(len(bucket) for bucket in classified.values()) == 1
    assert len(classified[EmlType.EML_110a]) == 1
