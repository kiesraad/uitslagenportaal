import pytest

from mainsite.utils.utils import name_to_slug


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Café Île", "cafe-ile"),
        ("Gemeenteraadsverkiezingen 2026", "gemeenteraadsverkiezingen-2026"),
        ("TK2023", "tk2023"),
        ("Provincie  Zuid-Holland", "provincie--zuidholland"),
        ("  Leading And Trailing  ", "leading-and-trailing"),
        ("MiXeD CaSe", "mixed-case"),
        ("", ""),
    ],
)
def test_name_to_slug(name, expected):
    assert name_to_slug(name) == expected
