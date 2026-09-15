from io import BytesIO
from os import path


class NamedBytesIO(BytesIO):
    """In-memory binary file that carries a file name, like a file on disk does."""

    def __init__(self, data: bytes, filename: str) -> None:
        super().__init__(data)
        self.filename = filename

    def __str__(self) -> str:
        return f"<NamedBytesIO {self.filename}>"

    @property
    def name(self) -> str:
        return self.filename

    @property
    def suffix(self) -> str:
        return path.splitext(self.filename)[1]
