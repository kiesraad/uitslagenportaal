from io import BytesIO
from pathlib import Path


class NamedBytesIO(BytesIO):
    """In-memory binary file that carries a file name, like a file on disk does."""

    def __init__(self, data: bytes, filename: str) -> None:
        super().__init__(data)
        self.filename = filename
        self.path = Path(filename)

    def __str__(self) -> str:
        return f"<NamedBytesIO {self.name}>"

    def __getattr__(self, item):
        """Forward attributes to self.path, so a NamedBytesIO is compatible with a Path object."""
        if hasattr(self.path, item):
            return getattr(self.path, item)

        return super().__getattribute__(item)
