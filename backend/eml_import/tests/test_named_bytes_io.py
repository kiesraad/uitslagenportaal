import pytest

from eml_import.utils.named_bytes_io import NamedBytesIO


def test_reads_its_content_like_a_file():
    file = NamedBytesIO(b"<eml/>", "telling.eml.xml")

    assert file.read() == b"<eml/>"
    file.seek(0)
    assert file.read(4) == b"<eml"


def test_exposes_path_attributes_of_the_filename():
    file = NamedBytesIO(b"", "telling.eml.xml")

    assert file.name == "telling.eml.xml"
    assert file.stem == "telling.eml"
    assert file.suffix == ".xml"
    assert file.suffixes == [".eml", ".xml"]


def test_unknown_attr_raises():
    file = NamedBytesIO(b"", "test.txt")

    with pytest.raises(AttributeError):
        _ = file.random_attr


def test_name_drops_the_directory_of_a_zip_entry():
    file = NamedBytesIO(b"", "Gemeente Utrecht/telling.eml.xml")

    assert file.name == "telling.eml.xml"
    assert file.filename == "Gemeente Utrecht/telling.eml.xml"
    assert file.parent.name == "Gemeente Utrecht"


def test_str_shows_the_name():
    assert str(NamedBytesIO(b"", "dir/telling.eml.xml")) == "<NamedBytesIO telling.eml.xml>"
