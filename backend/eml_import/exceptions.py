class EMLImporterException(Exception):
    """Exception raised for errors encountered during EML import operations."""


class PDFImporterException(Exception):
    """Exception raised for errors encountered during PDF import operations."""


class InvalidPDFException(PDFImporterException):
    """The PDF itself is wrong: unreadable, or its metadata is missing or invalid."""


class GithubImportException(Exception):
    """Exception raised for errors encountered during EML imports from GitHub."""


class FileAlreadyImported(Exception):
    """Exception raised for when an EML is already imported successfully."""
