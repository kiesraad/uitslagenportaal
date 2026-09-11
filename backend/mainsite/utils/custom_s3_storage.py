from botocore.auth import S3SigV4QueryAuth
from botocore.awsrequest import AWSRequest
from storages.backends.s3 import S3Storage

# boto3 spells the response-header overrides in camel case, the query string in the
# header names themselves.
RESPONSE_HEADER_PARAMETERS = {
    "ResponseCacheControl": "response-cache-control",
    "ResponseContentDisposition": "response-content-disposition",
    "ResponseContentEncoding": "response-content-encoding",
    "ResponseContentLanguage": "response-content-language",
    "ResponseContentType": "response-content-type",
    "ResponseExpires": "response-expires",
}


class SignedCustomDomainS3Storage(S3Storage):
    """
    S3 storage that signs the public URL instead of the endpoint it uploads through.

    Mainly needed locally, where the bucket is reached under a different hostname from the backend and the browser.
    Signing needs no connection, though, so the public URL is signed as it stands.

    ``custom_domain`` has to agree with ``addressing_style``: path style carries the
    bucket as the first path segment, virtual-host style as a subdomain.
    """

    def __init__(self, **settings):
        super().__init__(**settings)
        self._signing_credentials = None

    def url(self, name, parameters=None, expire=None, http_method=None):
        # Without a custom domain the parent presigns against its own endpoint already.
        if not self.custom_domain or not self.querystring_auth or self.cloudfront_signer:
            return super().url(name, parameters, expire, http_method)

        # The parent hands these to the query string rather than to boto3, which is the
        # only place the parameters are spelled the boto3 way.
        parameters = {RESPONSE_HEADER_PARAMETERS.get(key, key): value for key, value in (parameters or {}).items()}
        url = super().url(name, parameters, expire, http_method)

        if self._signing_credentials is None:
            self._signing_credentials = self._create_session().get_credentials()

        request = AWSRequest(method=http_method or "GET", url=url)
        # The S3 variant leaves the path unnormalised and signs an unsigned payload,
        # which is what the store expects for a presigned URL.
        S3SigV4QueryAuth(
            self._signing_credentials.get_frozen_credentials(),
            "s3",
            self.region_name,
            expires=self.querystring_expire if expire is None else expire,
        ).add_auth(request)
        return request.url
