import logging

from pv_scraper.utils.site_crawler import log_crawl


def test_log_crawl_keeps_the_query_string_out_of_the_message(caplog):
    url = "https://example.nl/uploads/pv.pdf?cb=ugr95lVd"

    with caplog.at_level(logging.INFO, logger="pv_scraper.utils.site_crawler"):
        log_crawl(url, "file download (status %d)", 200)

    [record] = caplog.records
    assert (record.getMessage(), record.url) == (
        "Crawled https://example.nl/uploads/pv.pdf: file download (status 200)",
        url,
    )
