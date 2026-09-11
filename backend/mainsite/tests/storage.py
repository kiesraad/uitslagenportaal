from django.core.files.storage import InMemoryStorage


class InMemoryPresignStorage(InMemoryStorage):
    """
    In-memory storage that accepts the presign arguments the S3 backend takes.

    Django's own storages stop at ``url(name)``, so a view asking for a signed
    response header would fail on the test double alone. The arguments cannot shape a
    plain in-memory URL; they are recorded per name so tests can assert on them.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url_parameters = {}

    def url(self, name, parameters=None, expire=None, http_method=None):
        self.url_parameters[name] = parameters or {}
        return super().url(name)
