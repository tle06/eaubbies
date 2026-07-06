import logging
from pathlib import Path

import cv2
import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)

# Default Tesseract config:
#   --psm 7  = single text line (best for a row of digits)
#   --oem 1  = LSTM engine only (most accurate)
#   -c tessedit_char_whitelist = restrict to digits and decimal separator
DEFAULT_CONFIG = "--psm 7 --oem 1 -c tessedit_char_whitelist=0123456789."


class TesseractClient:
    """
    Tesseract OCR wrapper optimised for water-meter digit reading.

    The caller (service.py) is responsible for all image-pipeline steps
    (crop, contrast, sharpen …).  This client only applies the minimal
    Tesseract-specific preparation that is always required regardless of
    the upstream pipeline:

      1. Convert BGR → greyscale.
      2. Upscale 3x  — Tesseract degrades sharply on small images.
      3. Gaussian blur to suppress compression/sensor noise.
      4. Otsu binarisation with adaptive polarity correction
         (works for both dark-on-light and light-on-dark meters).
      5. White border padding so Tesseract has breathing room.
    """

    default_folder = "../frames"

    def __init__(self, tesseract_cmd: str = None, save_frame: bool = True):
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
            logger.info(f"Tesseract binary set to: {tesseract_cmd}")
        self.save_frame = save_frame

    def write_output_file(self, name: str, image):
        filename = f"{name}.jpg"
        path_str = f"{self.default_folder}/{filename}"
        fullpath = Path(path_str)
        fullpath.parent.mkdir(parents=True, exist_ok=True)
        image.save(fullpath)
        logger.info(f"Frame saved at {str(fullpath)}")
        return fullpath

    @staticmethod
    def _prepare_for_tesseract(frame):
        """
        Minimal Tesseract-specific preparation applied to the already
        pipeline-processed frame coming from service.py.
        """
        # 1 – greyscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 2 – 3x upscale
        gray = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        logger.info("Frame upscaled 3x for Tesseract")

        # 3 – Gaussian blur
        gray = cv2.GaussianBlur(gray, (3, 3), 0)

        # 4 – Otsu binarisation (dark text on white)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Adaptive polarity: if digits came out white, flip them dark
        if cv2.countNonZero(binary) > binary.size * 0.5:
            binary = cv2.bitwise_not(binary)
            logger.info("Binary image inverted (light-on-dark source detected)")

        # 5 – white border
        binary = cv2.copyMakeBorder(
            binary, 40, 40, 40, 40, cv2.BORDER_CONSTANT, value=[255, 255, 255]
        )

        return binary

    def process_image(
        self,
        frame=None,
        image_path: str = None,
        config: str = DEFAULT_CONFIG,
        filename: str = "tesseract_optimized",
    ):
        """
        Run Tesseract OCR on a pipeline-processed frame or image path.

        Parameters
        ----------
        frame       : numpy.ndarray  BGR frame already processed by service.py pipeline.
        image_path  : str            Path to an image file (bypasses preparation).
        config      : str            Tesseract config string.
        filename    : str            Base name for the debug frame saved to disk.

        Returns
        -------
        (result_pages, text_regions)  same structure as AzureClient.
        """
        if image_path:
            image = Image.open(image_path)
            logger.info(f"Loaded image from path: {image_path}")
        elif frame is not None:
            logger.info("Applying Tesseract-specific preparation to pipeline frame")
            prepared = self._prepare_for_tesseract(frame)
            image = Image.fromarray(prepared)
            if self.save_frame:
                self.write_output_file(image=image, name=filename)
        else:
            raise ValueError("Either 'frame' or 'image_path' must be provided.")

        try:
            data = pytesseract.image_to_data(
                image, output_type=pytesseract.Output.DICT, config=config
            )
            raw_text = pytesseract.image_to_string(image, config=config)
            logger.info(f"Tesseract raw OCR text: '{raw_text.strip()}'")

            class MockLine:
                def __init__(self, text, bounding_box=None):
                    self.text = text
                    self.bounding_box = bounding_box or [0, 0, 0, 0, 0, 0, 0, 0]

            class MockResultPage:
                def __init__(self, lines):
                    self.lines = lines

            parsed_lines = [
                MockLine(line.strip()) for line in raw_text.split("\n") if line.strip()
            ]
            logger.info(f"Tesseract parsed {len(parsed_lines)} non-empty line(s)")

            text_regions = []
            for i in range(len(data["text"])):
                try:
                    conf = int(data["conf"][i])
                except (ValueError, TypeError):
                    conf = -1
                if conf > 0:
                    text = data["text"][i].strip()
                    if text:
                        x = data["left"][i]
                        y = data["top"][i]
                        w = data["width"][i]
                        h = data["height"][i]
                        bounding_box = [x, y, x + w, y, x + w, y + h, x, y + h]
                        text_regions.append(
                            {"bounding_box": bounding_box, "text": text}
                        )
            logger.debug(
                f"Tesseract regions with confidence > 0: {len(text_regions)}"
            )

            return [MockResultPage(parsed_lines)], text_regions

        except Exception as e:
            logger.error(f"Tesseract error: {e}", exc_info=True)
            raise
