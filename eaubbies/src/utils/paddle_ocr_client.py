import logging
from pathlib import Path

import cv2
from PIL import Image

logger = logging.getLogger(__name__)


class PaddleOCRClient:
    """
    Drop-in replacement for TesseractClient / AzureClient using PaddleOCR
    (PP-OCRv4 mobile model by default) for fully local, offline digit recognition.

    The caller (service.py) is responsible for all image-pipeline steps.
    This client passes the already-processed frame straight to the OCR engine
    with no additional preprocessing — PaddleOCR handles raw BGR frames natively.

    Return signature of process_image() mirrors AzureClient / TesseractClient
    so service.py needs only a one-line engine check.

    Installation
    ------------
    Lightweight (recommended for Raspberry Pi / embedded):
        pip install rapidocr-onnxruntime
        # or: uv sync --extra paddleocr-lite

    Full PaddleOCR stack (highest accuracy):
        pip install paddlepaddle paddleocr
        # or: uv sync --extra paddleocr-full
    """

    default_folder = "../frames"

    def __init__(
        self,
        use_angle_cls: bool = False,
        lang: str = "en",
        use_gpu: bool = False,
        save_frame: bool = True,
        backend: str = "auto",
    ):
        """
        Parameters
        ----------
        use_angle_cls : bool   Enable text-angle classifier (not needed for upright digits).
        lang          : str    Language code for PaddleOCR ("en" covers digits well).
        use_gpu       : bool   Use GPU inference if available.
        save_frame    : bool   Write the input frame to disk for debugging.
        backend       : str
            "rapid"  – RapidOCR ONNX  (rapidocr-onnxruntime, no PaddlePaddle)
            "paddle" – full PaddleOCR  (paddlepaddle + paddleocr)
            "auto"   – try RapidOCR first, fall back to PaddleOCR
        """
        self.save_frame = save_frame
        self._ocr = None
        self._backend = None

        if backend in ("rapid", "auto"):
            try:
                from rapidocr_onnxruntime import RapidOCR
                self._ocr = RapidOCR()
                self._backend = "rapid"
                logger.info("PaddleOCRClient: using RapidOCR (ONNX) backend")
            except ImportError:
                if backend == "rapid":
                    raise ImportError(
                        "rapidocr-onnxruntime not installed. "
                        "Run: pip install rapidocr-onnxruntime"
                    )
                logger.info("RapidOCR not available, falling back to PaddleOCR")

        if self._ocr is None:
            try:
                from paddleocr import PaddleOCR
                self._ocr = PaddleOCR(
                    use_angle_cls=use_angle_cls,
                    lang=lang,
                    use_gpu=use_gpu,
                    show_log=False,
                )
                self._backend = "paddle"
                logger.info("PaddleOCRClient: using PaddleOCR backend")
            except ImportError:
                raise ImportError(
                    "No OCR backend found. Install one of:\n"
                    "  pip install rapidocr-onnxruntime   (lightweight)\n"
                    "  pip install paddlepaddle paddleocr  (full accuracy)"
                )

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def write_output_file(self, name: str, image):
        filename = f"{name}.jpg"
        path_str = f"{self.default_folder}/{filename}"
        fullpath = Path(path_str)
        fullpath.parent.mkdir(parents=True, exist_ok=True)
        image.save(fullpath)
        logger.info(f"Frame saved at {str(fullpath)}")
        return fullpath

    # ------------------------------------------------------------------
    # public API  (mirrors TesseractClient / AzureClient)
    # ------------------------------------------------------------------

    def process_image(
        self,
        frame=None,
        image_path: str = None,
        filename: str = "paddle_optimized",
        config: str = "",   # accepted for API compatibility, not used
    ):
        """
        Run PaddleOCR on a pipeline-processed frame or image path.
        No additional preprocessing is applied — the frame from service.py
        is passed directly to the OCR engine.

        Returns
        -------
        (result_pages, text_regions)  same structure as TesseractClient.
        """
        if image_path:
            img = cv2.imread(str(image_path))
            if img is None:
                raise FileNotFoundError(f"Could not open image: {image_path}")
            logger.info(f"Loaded image from path: {image_path}")
        elif frame is not None:
            img = frame
            logger.info("Using pipeline frame directly (no additional preprocessing)")
            if self.save_frame:
                self.write_output_file(
                    image=Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)),
                    name=filename,
                )
        else:
            raise ValueError("Either 'frame' or 'image_path' must be provided.")

        try:
            if self._backend == "rapid":
                raw_results, _ = self._ocr(img)
                ocr_lines = raw_results if raw_results else []
                paddle_format = [
                    [box, (text, score)]
                    for box, text, score in (
                        (r[0], r[1][0], r[1][1]) for r in ocr_lines
                    )
                ]
            else:
                raw_results = self._ocr.ocr(img, cls=False)
                paddle_format = raw_results[0] if raw_results and raw_results[0] else []

            logger.info(f"PaddleOCR raw results: {len(paddle_format)} region(s)")

            class MockLine:
                def __init__(self, text, bounding_box=None):
                    self.text = text
                    self.bounding_box = bounding_box or [0, 0, 0, 0, 0, 0, 0, 0]

            class MockResultPage:
                def __init__(self, lines):
                    self.lines = lines

            text_regions = []
            parsed_lines = []

            for entry in paddle_format:
                box_pts = entry[0]          # [[x1,y1],[x2,y1],[x2,y2],[x1,y2]]
                text = entry[1][0].strip()
                conf = float(entry[1][1])

                if not text:
                    continue

                flat_box = [coord for pt in box_pts for coord in pt]
                parsed_lines.append(MockLine(text=text, bounding_box=flat_box))
                text_regions.append({"bounding_box": flat_box, "text": text})
                logger.info(f"PaddleOCR detected: '{text}' (conf={conf:.3f})")

            logger.info(f"PaddleOCR parsed {len(parsed_lines)} non-empty line(s)")
            return [MockResultPage(parsed_lines)], text_regions

        except Exception as e:
            logger.error(f"PaddleOCR error: {e}", exc_info=True)
            raise
