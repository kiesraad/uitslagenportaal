from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import FileSystemStorage, Storage, storages


class PrefixedStorage(Storage):
    """A storage rooted at a prefix of another storage. Names passed in are relative to that prefix."""

    def __init__(self, storage: Storage, prefix: str):
        self.storage = storage
        self.prefix = prefix.strip("/")

    def _key(self, name: str) -> str:
        name = name.strip("/")
        if not self.prefix:
            return name
        return f"{self.prefix}/{name}" if name else self.prefix

    def listdir(self, path):
        return self.storage.listdir(self._key(path))

    def open(self, name, mode="rb"):
        return self.storage.open(self._key(name), mode)

    def size(self, name):
        return self.storage.size(self._key(name))


class PvImportStorage(Storage):
    """
    Source of proces-verbaal PDFs for import_pvs.

    PV_IMPORT_SOURCE picks the backend: a FileSystemStorage for a folder, or a prefix
    of another storage alias (the app bucket by default) for s3.
    """

    def __init__(self):
        source = settings.PV_IMPORT_SOURCE
        if source == "folder":
            location = Path(settings.PV_IMPORT_FOLDER).resolve()
            if not location.is_dir():
                raise ImproperlyConfigured(f"Folder does not exist: {location}")
            self.storage = FileSystemStorage(location=location)
            return
        if source == "s3":
            prefix = settings.PV_IMPORT_PREFIX.strip("/")
            if not prefix:
                raise ImproperlyConfigured("PV_IMPORT_PREFIX is empty; refusing to scan the whole bucket.")
            self.storage = PrefixedStorage(storages[settings.PV_IMPORT_STORAGE], prefix)
            return
        raise ImproperlyConfigured(f"PV_IMPORT_SOURCE must be 'folder' or 's3', got {source!r}.")

    def listdir(self, path):
        return self.storage.listdir(path)

    def open(self, name, mode="rb"):
        return self.storage.open(name, mode)

    def size(self, name):
        return self.storage.size(name)
