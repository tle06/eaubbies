import logging
from pathlib import Path

import cv2
from PIL import Image

logger = logging.getLogger(__name__)


class PaddleOCRClient:
    """
    Drop-in replacement for TesseractClient / AzureClient that uses PaddleOCR
    (PP-OCRv4 mobile model by default) for fully local, offline digit recognition.

    The return signature of process_image() mirrors AzureClient so service.py
    needs only a one-line engine check — no other changes required.

    Installation
    ------------
    Option A – full PaddlePaddle stack (more accurate, larger install):
        pip install paddlepaddle paddleocr

    Option B – lightweight ONNX runtime wrapper, zero heavy deps (recommended
    for Raspberry Pi / embedded use):
        pip install rapidocr-onnxruntime
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
        use_angle_cls : bool
            Enable text-angle classifier (not needed for upright meter digits).
        lang : str
            Language code passed to PaddleOCR ("en" covers digits well).
        use_gpu : bool
            Use GPU inference if available.
        save_frame : bool
            Write the preprocessed frame to disk for debugging.
        backend : str
            "paddle"  – use full PaddleOCR (paddlepaddle + paddleocr)
            "rapid"   – use RapidOCR (rapidocr-onnxruntime, no PaddlePaddle needed)
            "auto"    – try RapidOCR first, fall back to PaddleOCR
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
                        "rapidocr-onnxruntime is not installed. "
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
                    "  pip install rapidocr-onnxruntime   (lightweight, recommended)\n"
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

    @staticmethod
    def _preprocess(frame):
        """
        Lightweight preprocessing for PaddleOCR — less aggressive than the
        Tesseract pipeline because PaddleOCR handles more variation natively:
        1. Convert to greyscale.
        2. Upscale 2x (helps on very small crops; PaddleOCR is more robust than
           Tesseract on small inputs so 2x is enough).
        3. Convert back to BGR (PaddleOCR expects a 3-channel image).
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        return bgr

    # ------------------------------------------------------------------
    # public API  (mirrors TesseractClient / AzureClient)
    # ------------------------------------------------------------------

    def process_image(
        self,
        frame=None,
        image_path: str = None,
        filename: str = "paddle_optimized",
        # config kwarg accepted but ignored (kept for API compatibility)
        config: str = "",
    ):
        """
        Run PaddleOCR on a frame or image path.

        Returns
        -------
        (result_pages, text_regions)
            Same structure as TesseractClient.process_image() so service.py
            requires no changes.
        """
        if image_path:
            img = cv2.imread(str(image_path))
            if img is None:
                raise FileNotFoundError(f"Could not open image: {image_path}")
            logger.info(f"Loaded image from path: {image_path}")
        elif frame is not None:
            logger.info("Preprocessing frame for PaddleOCR")
            img = self._preprocess(frame)
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
                # RapidOCR result: list of [[[x,y],...], (text, score)]
                ocr_lines = raw_results if raw_results else []
                paddle_format = [
                    [box, (text, score)]
                    for box, text, score in (
                        (r[0], r[1][0], r[1][1]) for r in ocr_lines
                    )
                ]
            else:
                raw_results = self._ocr.ocr(img, cls=False)
                # PaddleOCR result: list of pages, each page is list of
                # [[[x,y],...], (text, score)]
                paddle_format = raw_results[0] if raw_results and raw_results[0] else []

            logger.info(f"PaddleOCR raw results ({len(paddle_format)} region(s))")
            for entry in paddle_format:
                logger.debug(f"  region text='{entry[1][0]}' conf={entry[1][1]:.3f}")

            # --- Build MockLine / MockResultPage (same shape as TesseractClient) ---

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
                box_pts = entry[0]   # [[x1,y1],[x2,y1],[x2,y2],[x1,y2]]
                text = entry[1][0].strip()
                conf = float(entry[1][1])

                if not text:
                    continue

                # Flatten box to the 8-value format used elsewhere
                flat_box = [coord for pt in box_pts for coord in pt]

                parsed_lines.append(MockLine(text=text, bounding_box=flat_box))
                text_regions.append({"bounding_box": flat_box, "text": text})
                logger.info(f"PaddleOCR detected: '{text}' (conf={conf:.3f})")

            logger.info(
                f"PaddleOCR parsed {len(parsed_lines)} non-empty line(s)"
            )

            return [MockResultPage(parsed_lines)], text_regions

        except Exception as e:
            logger.error(
                f"Error processing image with PaddleOCR: {e}", exc_info=True
            )
            raise
