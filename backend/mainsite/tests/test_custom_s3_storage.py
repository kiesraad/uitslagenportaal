from datetime import datetime, timezone
from urllib.parse import parse_qs, urlsplit

import boto3
import pytest
from botocore.config import Config

from mainsite.utils.custom_s3_storage import SignedCustomDomainS3Storage

ACCESS_KEY = "uitslagenportaal"
SECRET_KEY = "password"
REGION = "nl-ams"
BUCKET = "uitslagenportaal"
ENDPOINT_URL = "http://object-storage:9000"
KEY = "GR2026/Telling GR2026 gemeente Zwolle.eml.xml"


def build_storage(**overrides):
    options = {
        "bucket_name": BUCKET,
        "endpoint_url": ENDPOINT_URL,
        "access_key": ACCESS_KEY,
        "secret_key": SECRET_KEY,
        "region_name": REGION,
        "addressing_style": "path",
        "custom_domain": f"localhost:9000/{BUCKET}",
        "url_protocol": "http:",
        "querystring_auth": True,
    }
    return SignedCustomDomainS3Storage(**{**options, **overrides})


def presign_with_boto3(endpoint_url, addressing_style, key, parameters=None):
    """The URL boto3 hands out for a store that is reachable under one name."""
    client = boto3.Session(
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
    ).client(
        "s3",
        region_name=REGION,
        endpoint_url=endpoint_url,
        config=Config(s3={"addressing_style": addressing_style}, signature_version="s3v4"),
    )
    params = {"Bucket": BUCKET, "Key": key, **(parameters or {})}
    return client.generate_presigned_url("get_object", Params=params, ExpiresIn=3600)


def signature(url):
    return parse_qs(urlsplit(url).query)["X-Amz-Signature"]


@pytest.fixture
def fixed_signing_clock(monkeypatch):
    """SigV4 stamps the signing moment into the URL, so pin it before comparing signatures."""
    monkeypatch.setattr(
        "botocore.auth.get_current_datetime",
        lambda: datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
    )


def test_url_is_signed_for_the_public_host():
    url = build_storage().url(KEY)

    assert url.startswith("http://localhost:9000/uitslagenportaal/GR2026/Telling%20GR2026%20gemeente%20Zwolle.eml.xml?")
    query = parse_qs(urlsplit(url).query)
    assert query["X-Amz-Algorithm"] == ["AWS4-HMAC-SHA256"]
    assert query["X-Amz-SignedHeaders"] == ["host"]
    assert query["X-Amz-Expires"] == ["3600"]
    assert query["X-Amz-Credential"] == [f"{ACCESS_KEY}/{datetime.now(timezone.utc):%Y%m%d}/{REGION}/s3/aws4_request"]


@pytest.mark.parametrize(
    ("custom_domain", "url_protocol", "addressing_style", "public_endpoint_url"),
    [
        (f"localhost:9000/{BUCKET}", "http:", "path", "http://localhost:9000"),
        (f"{BUCKET}.s3.nl-ams.scw.cloud", "https:", "virtual", "https://s3.nl-ams.scw.cloud"),
    ],
)
def test_signature_matches_a_real_presign(
    fixed_signing_clock, custom_domain, url_protocol, addressing_style, public_endpoint_url
):
    storage = build_storage(
        custom_domain=custom_domain,
        url_protocol=url_protocol,
        addressing_style=addressing_style,
    )

    url = storage.url(KEY)

    expected = presign_with_boto3(public_endpoint_url, addressing_style, KEY)
    assert urlsplit(url).netloc == urlsplit(expected).netloc
    assert urlsplit(url).path == urlsplit(expected).path
    assert signature(url) == signature(expected)


def test_expiry_can_be_overridden_per_url():
    url = build_storage().url(KEY, expire=60)

    assert parse_qs(urlsplit(url).query)["X-Amz-Expires"] == ["60"]


def test_without_a_custom_domain_the_endpoint_is_signed(fixed_signing_clock):
    url = build_storage(custom_domain="").url(KEY)

    assert urlsplit(url).netloc == "object-storage:9000"
    assert signature(url) == signature(presign_with_boto3(ENDPOINT_URL, "path", KEY))


def test_unsigned_urls_stay_unsigned():
    url = build_storage(querystring_auth=False).url(KEY)

    assert url == "http://localhost:9000/uitslagenportaal/GR2026/Telling%20GR2026%20gemeente%20Zwolle.eml.xml"


def test_response_headers_are_signed_into_the_url(fixed_signing_clock):
    parameters = {"ResponseContentDisposition": "attachment"}

    url = build_storage().url(KEY, parameters=parameters)

    assert parse_qs(urlsplit(url).query)["response-content-disposition"] == ["attachment"]
    expected = presign_with_boto3("http://localhost:9000", "path", KEY, parameters=parameters)
    assert signature(url) == signature(expected)
