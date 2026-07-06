# eaubbies/eaubbies/src/utils/tesseract_client.py
import pytesseract
import cv2
import logging
from PIL import Image
from pathlib import Path

logger = logging.getLogger(__name__)


class TesseractClient:
    """
    Client wrapper for Tesseract OCR.
    """

    default_folder = "../frames"

    def __init__(self, tesseract_cmd: str = None, save_frame: bool = True):
        """
        Initialize the Tesseract Client.
        """
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

    def process_image(
        self,
        frame=None,
        image_path: str = None,
        config: str = "--psm 8 -c tessedit_char_whitelist=0123456789",
        filename: str = "tesseract_optimized",
    ):
        """
        Process an image using pytesseract OCR.

        Parameters:
            frame (numpy.ndarray): OpenCV image frame.
            image_path (str): Path to local image file.
            config (str): Tesseract config string.

        Returns:
            list: A structure mimicking AzureClient's read result format to ease integration.
        """
        if image_path:
            image = Image.open(image_path)
            logger.info(f"Loaded image from path: {image_path}")
        elif frame is not None:
            logger.info("Processing frame through Tesseract preprocessing pipeline")
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            coords = cv2.findNonZero(cv2.bitwise_not(gray))
            if coords is not None:
                x, y, w, h = cv2.boundingRect(coords)
                gray = gray[y : y + h, x : x + w]
                logger.info(f"Auto-crop applied: x={x} y={y} w={w} h={h}")

            gray = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
            logger.info("Image upscaled 3x for Tesseract")

            _, binary = cv2.threshold(
                gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
            )

            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            morph = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            morph = cv2.dilate(morph, kernel, iterations=1)

            final_cv_image = cv2.bitwise_not(morph)

            final_cv_image = cv2.copyMakeBorder(
                final_cv_image,
                40,
                40,
                40,
                40,
                cv2.BORDER_CONSTANT,
                value=[255, 255, 255],
            )
            image = Image.fromarray(final_cv_image)
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
            n_boxes = len(data["text"])
            for i in range(n_boxes):
                try:
                    conf = int(data["conf"][i])
                except (ValueError, TypeError):
                    conf = -1
                if conf > 0:
                    text = data["text"][i].strip()
                    if text:
                        x, y, w, h = (
                            data["left"][i],
                            data["top"][i],
                            data["width"][i],
                            data["height"][i],
                        )
                        bounding_box = [x, y, x + w, y, x + w, y + h, x, y + h]
                        text_regions.append(
                            {"bounding_box": bounding_box, "text": text}
                        )
            logger.debug(
                f"Tesseract word-level regions with confidence > 0: {len(text_regions)}"
            )

            result_pages = [MockResultPage(parsed_lines)]
            return result_pages, text_regions

        except Exception as e:
            logger.error(f"Error processing image with Tesseract: {e}", exc_info=True)
            raise e
