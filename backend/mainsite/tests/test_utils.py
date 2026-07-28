import pytest

from mainsite.utils.utils import name_to_slug


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Café Île", "cafe_ile"),
        ("Gemeenteraadsverkiezingen 2026", "gemeenteraadsverkiezingen_2026"),
        ("TK2023", "tk2023"),
        ("Provincie  Zuid-Holland", "provincie__zuidholland"),
        ("  Leading And Trailing  ", "leading_and_trailing"),
        ("MiXeD CaSe", "mixed_case"),
        ("", ""),
    ],
)
def test_name_to_slug(name, expected):
    assert name_to_slug(name) == expected
