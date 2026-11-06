def test_report_technical_issue_redirects_to_the_configured_address(client, settings):
    settings.TECHNICAL_ISSUE_EMAIL = "issues@example.test"

    response = client.get("/api/report-technical-issue/")

    assert response.status_code == 302
    assert response["Location"] == "mailto:issues@example.test"


def test_report_technical_issue_redirects_to_an_empty_mailto_when_unconfigured(client, settings):
    settings.TECHNICAL_ISSUE_EMAIL = ""

    response = client.get("/api/report-technical-issue/")

    assert response.status_code == 302
    assert response["Location"] == "mailto:"
