"""Readers of the handwritten numbers on a PV: one crop of a field in, the digits written there out."""

import importlib
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

from PIL import Image

from pv_ocr.utils.ocr import TO_DIGIT

# Imported only when chosen, so the app does not need the ML dependencies of every reader.
READERS = {
    "trocr": "pv_ocr.readers.trocr.TrOCRReader",
}


@dataclass(frozen=True)
class Reading:
    digits: str  # empty when nothing is written
    confidence: float  # 0 to 1


class NumberReader(ABC):
    @abstractmethod
    def read(self, images: list[Image.Image]) -> list[Reading]:
        """A reading per image, in order."""


def get_reader(name: str, **options) -> NumberReader:
    if name not in READERS:
        raise ValueError(f"Unknown reader {name!r}; known are {', '.join(sorted(READERS))}")
    module, _, cls = READERS[name].rpartition(".")
    return getattr(importlib.import_module(module), cls)(**options)


def to_digits(text: str) -> str:
    """The digits in `text`, with letters that look like digits read as those."""
    return re.sub(r"\D", "", text.translate(TO_DIGIT))
