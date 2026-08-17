# eaubbies/eaubbies/src/utils/tesseract_client.py
import pytesseract
import cv2
import numpy as np
import logging
from PIL import Image
from pathlib import Path

logger = logging.getLogger(__name__)


class TesseractClient:
    """
    Thin wrapper around ``pytesseract`` that preprocesses a frame for OCR and
    returns results in the same shape used by :class:`AzureClient`, so both
    OCR engines are interchangeable in ``service.service_process``.
    """

    default_folder = "../frames"

    def __init__(self, tesseract_cmd: str = None, save_frame: bool = True):
        """
        Initialise the Tesseract client.

        Parameters:
            tesseract_cmd (str): Optional absolute path to the ``tesseract``
                binary. Only needed when it is not on ``PATH`` (e.g. a local
                macOS dev host). Inside the container it is left unset.
            save_frame (bool): When True the preprocessed image is written to
                ``default_folder`` for debugging/UI display.
        """
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
            logger.info(f"Tesseract binary set to: {tesseract_cmd}")
        self.save_frame = save_frame

    @staticmethod
    def _to_grayscale(frame):
        """
        Return a single-channel greyscale copy of *frame*.

        The upstream image pipeline may hand us a frame that is already
        greyscale (``convert_to_grey`` is enabled by default). Calling
        ``cv2.cvtColor(frame, COLOR_BGR2GRAY)`` on such a frame raises, which
        was the root cause of the Tesseract path failing. This helper inspects
        the array shape and only converts when the frame is multi-channel.

        Parameters:
            frame (numpy.ndarray): 2-D greyscale or 3-D BGR image.

        Returns:
            numpy.ndarray: A 2-D ``uint8`` greyscale image.
        """
        if frame is None:
            raise ValueError("frame must not be None")
        # 2-D array or explicit single channel -> already greyscale.
        if frame.ndim == 2 or (frame.ndim == 3 and frame.shape[2] == 1):
            gray = frame if frame.ndim == 2 else frame[:, :, 0]
        else:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # Tesseract preprocessing (threshold/morphology) assumes uint8.
        if gray.dtype != np.uint8:
            gray = np.clip(gray, 0, 255).astype(np.uint8)
        return gray

    def write_output_file(self, name: str, image):
        """
        Persist a PIL *image* as ``<name>.jpg`` inside ``default_folder``.

        Parameters:
            name (str): Base filename without extension.
            image (PIL.Image.Image): Image to write.

        Returns:
            pathlib.Path: Full path of the written file.
        """
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
        config: str = "--psm 7 --oem 1 -c tessedit_char_whitelist=0123456789.",
        filename: str = "tesseract_optimized",
    ):
        """
        Process an image using pytesseract OCR.

        Accepts either a pre-loaded OpenCV *frame* (greyscale or BGR) or a path
        to an image on disk. The frame is converted to greyscale defensively
        (see :meth:`_to_grayscale`), auto-cropped to the dark content, upscaled,
        binarised (Otsu) and morphologically cleaned before OCR.

        Parameters:
            frame (numpy.ndarray): OpenCV image frame (2-D grey or 3-D BGR).
            image_path (str): Path to a local image file (alternative to frame).
            config (str): Tesseract config string (page-segmentation mode,
                whitelist, etc.).
            filename (str): Base name used when saving the preprocessed image.

        Returns:
            tuple: ``(result_pages, text_regions)`` where ``result_pages`` is a
            list of objects exposing ``.lines`` (each line has ``.text``) and
            ``text_regions`` is a list of ``{"bounding_box", "text"}`` dicts,
            mirroring :class:`AzureClient` output for a drop-in integration.
        """
        if image_path:
            image = Image.open(image_path)
            logger.info(f"Loaded image from path: {image_path}")
        elif frame is not None:
            logger.info("Processing frame through Tesseract preprocessing pipeline")
            gray = self._to_grayscale(frame)

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
