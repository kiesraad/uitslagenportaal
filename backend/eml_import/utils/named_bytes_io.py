from io import BytesIO
from pathlib import Path


class NamedBytesIO(BytesIO):
    """In-memory binary file that carries a file name, like a file on disk does."""

    @staticmethod
    def from_path(path: Path) -> NamedBytesIO:
        return NamedBytesIO(path.read_bytes(), path)

    def __init__(self, data: bytes, filename: str | Path) -> None:
        super().__init__(data)
        self.path = Path(filename)

    @property
    def filename(self):
        return self.name

    def __str__(self) -> str:
        return f"<NamedBytesIO {self.name}>"

    def __getattr__(self, item):
        """Forward attributes to self.path, so a NamedBytesIO is compatible with a Path object."""
        if hasattr(self.path, item):
            return getattr(self.path, item)

        return super().__getattribute__(item)
