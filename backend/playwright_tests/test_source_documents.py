"""
The source documents on the results pages: each level lists its own EML file and serves
it from object storage through a presigned redirect.
"""

import re
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

from playwright_tests.conftest import EML_FIXTURES

pytestmark = pytest.mark.playwright


@pytest.mark.parametrize(
    ("url", "name", "description", "fixture"),
    [
        pytest.param(
            "/ab2023/gsb/654-borsele/csb/17-scheldestromen/resultaten",
            "EML_NL tellingbestand 510b",
            "Output van de optelsoftware, bevat de resultaten van alle stembureaus en de optelling van de "
            "hele gemeente.",
            "ws/Telling_AB2023_Scheldestromen_gemeente_Borsele.eml.xml",
            id="gemeente-510b",
        ),
        pytest.param(
            "/ab2023/csb/17-scheldestromen/resultaten",
            "EML_NL tellingbestand 510d",
            "Output van de optelsoftware, bevat de resultaten van alle onderliggende regio's en de totaaltellingen.",
            "ws/Totaaltelling_AB2023_Scheldestromen_waterschap_Scheldestromen.eml.xml",
            id="csb-510d",
        ),
    ],
)
def test_the_results_page_downloads_its_source_document(page: Page, url, name, description, fixture):
    page.goto(url)
    expect(page.get_by_role("heading", name="Brondocumenten")).to_be_visible()

    document = page.get_by_role("link", name=re.compile(r"EML_NL tellingbestand"))
    expect(document).to_have_count(1)
    expect(document).to_contain_text(name)
    expect(document).to_contain_text(re.compile(r"\(xml, [\d,]+ KB\)"))
    expect(page.get_by_text(description, exact=True)).to_be_visible()

    with page.expect_download() as download_info:
        document.click()
    download = download_info.value

    # The presigned URL asks for an attachment without a filename, so the browser names
    # the file after the storage key.
    assert download.suggested_filename.endswith(".eml.xml")
    assert Path(download.path()).read_bytes() == (EML_FIXTURES / fixture).read_bytes()
