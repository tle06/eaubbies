# eaubbies/eaubbies/src/tests/test_service_ocr.py
"""Tests for the unified OCR adapters in :mod:`service`.

Both engine helpers must return the same ``(lines, text_regions)`` shape so the
downstream meter-parsing code has a single path. These tests stub the OCR
clients so no real Tesseract binary or Azure endpoint is required.
"""

import types

import service


class _Line:
    """Minimal line object exposing the ``.text`` attribute used downstream."""

    def __init__(self, text):
        self.text = text


def test_run_tesseract_ocr_flattens_pages(monkeypatch):
    """Tesseract pages are flattened into a single list of lines."""

    class _Page:
        def __init__(self, lines):
            self.lines = lines

    regions = [{"bounding_box": [0, 0, 1, 0, 1, 1, 0, 1], "text": "123"}]

    class _StubTesseract:
        def __init__(self, *args, **kwargs):
            self.default_folder = None

        def process_image(self, frame, config, filename):
            return [_Page([_Line("123"), _Line("456")])], regions

    monkeypatch.setattr(service, "TesseractClient", _StubTesseract)
    monkeypatch.setattr(service, "_draw_boxes", lambda *a, **k: None)

    config = types.SimpleNamespace(get_param=lambda *k: "cfg")
    lines, text_regions = service._run_tesseract_ocr(config, object(), "/tmp")

    assert [ln.text for ln in lines] == ["123", "456"]
    assert text_regions == regions


def test_run_azure_ocr_flattens_blocks(monkeypatch):
    """Azure blocks are flattened into a single list of lines."""

    block = types.SimpleNamespace(lines=[_Line("789")])
    read = types.SimpleNamespace(blocks=[block])
    result = types.SimpleNamespace(read=read)
    regions = [{"bounding_box": [0, 0, 1, 0, 1, 1, 0, 1], "text": "789"}]

    class _StubAzure:
        def __init__(self, *args, **kwargs):
            self.default_folder = None

        def process_image(self, frame):
            return result

        def get_regions(self, result):
            return regions

        def draw_text_boxes(self, text_regions, frame, filename):
            return None

    monkeypatch.setattr(service, "AzureClient", _StubAzure)

    config = types.SimpleNamespace(get_param=lambda *k: "x")
    lines, text_regions = service._run_azure_ocr(config, object(), "/tmp")

    assert [ln.text for ln in lines] == ["789"]
    assert text_regions == regions
