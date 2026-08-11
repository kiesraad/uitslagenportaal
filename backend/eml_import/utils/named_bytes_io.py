from io import BytesIO


class NamedBytesIO(BytesIO):
    """In-memory binary file that carries a file name, like a file on disk does."""

    def __init__(self, data: bytes, filename: str) -> None:
        super().__init__(data)
        self.filename = filename

    def __str__(self) -> str:
        return f"<NamedBytesIO {self.filename}>"
