from io import BytesIO
from pathlib import Path, PurePath
from typing import Self


class NamedBytesIO(BytesIO):
    """In-memory binary file that carries a file name, like a file on disk does."""

    @classmethod
    def from_path(cls, path: Path) -> Self:
        return cls(path.read_bytes(), path)

    def __init__(self, data: bytes, filename: str | PurePath) -> None:
        super().__init__(data)
        self.path = PurePath(filename)

    @property
    def filename(self):
        return str(self.path)

    def __str__(self) -> str:
        return f"<NamedBytesIO {self.name}>"

    def __getattr__(self, item):
        """Forward attributes to self.path, so a NamedBytesIO has a Path's name, stem and suffix. A PurePath has no
        methods that touch the disk, so neither does this."""
        if self.path and hasattr(self.path, item):
            return getattr(self.path, item)

        return super().__getattribute__(item)
