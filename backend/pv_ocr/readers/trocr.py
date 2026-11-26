"""Microsoft's TrOCR, a transformer that reads a line of handwriting; needs the backend's `ml` dependency group."""

import torch
from PIL import Image
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

from pv_ocr.readers import NumberReader, Reading, to_digits


class TrOCRReader(NumberReader):
    def __init__(self, checkpoint: str, batch_size: int = 16, device: str = "cpu"):
        self.processor = TrOCRProcessor.from_pretrained(checkpoint)
        self.model = VisionEncoderDecoderModel.from_pretrained(checkpoint).to(device).eval()
        self.batch_size = batch_size
        self.device = device

    def read(self, images: list[Image.Image]) -> list[Reading]:
        readings = []
        for start in range(0, len(images), self.batch_size):
            readings += self._read_batch(images[start : start + self.batch_size])
        return readings

    @torch.inference_mode()
    def _read_batch(self, images: list[Image.Image]) -> list[Reading]:
        pixels = self.processor(images=[image.convert("RGB") for image in images], return_tensors="pt").pixel_values
        output = self.model.generate(
            pixels.to(self.device), max_new_tokens=8, use_cache=True, output_scores=True, return_dict_in_generate=True
        )
        # The log-probability of each generated token; the padding after a sequence that ended early does not count.
        scores = self.model.compute_transition_scores(output.sequences, output.scores, normalize_logits=True)
        scores = scores.masked_fill(output.sequences[:, 1:] == self.model.generation_config.pad_token_id, 0)
        texts = self.processor.batch_decode(output.sequences, skip_special_tokens=True)
        # The sequence probability: the product of its token probabilities; 0 for one cut off before its end.
        finished = (output.sequences[:, 1:] == self.model.generation_config.eos_token_id).any(dim=1)
        confidences = (scores.sum(dim=1).exp() * finished).tolist()
        return [Reading(to_digits(text), confidence) for text, confidence in zip(texts, confidences)]
