"""Shared helpers for EML importer unit tests."""

from itertools import count

from eml_import.utils.named_bytes_io import NamedBytesIO

_fake_eml_seq = count()


def fake_eml_file(filename: str = "test.eml.xml") -> NamedBytesIO:
    """Stand-in file for importer unit tests that build EML in memory.

    Each call gets distinct bytes so ImportedEmlHash does not treat a later
    correction import as a duplicate of an earlier one in the same test.
    """
    return NamedBytesIO(f'<eml n="{next(_fake_eml_seq)}"/>'.encode(), filename)
