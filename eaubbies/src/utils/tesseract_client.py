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
        self.save_frame = save_frame

    def write_output_file(self, name: str, image):
        filename = f"{name}.jpg"
        path_str = f"{self.default_folder}/{filename}"
        fullpath = Path(path_str)
        fullpath.parent.mkdir(parents=True, exist_ok=True)
        image.save(fullpath)
        print("Frame saved at", str(fullpath))
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
            config (str): Tesseract config string (default is '--psm 8 -c tessedit_char_whitelist=0123456789' which assumes a single line of digits).

        Returns:
            list: A structure mimicking AzureClient's read result format to ease integration.
        """
        if image_path:
            image = Image.open(image_path)
            print(
                f"Loaded image from path: {image_path}"
            )  # Debug print to confirm image loading
        elif frame is not None:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # 2. AUTO-CROP: Remove the giant white mask added by 'fill_image_except_rectangle'
            # Find all pixels that are NOT pure white (the mask) and get their bounding box
            coords = cv2.findNonZero(cv2.bitwise_not(gray))
            if coords is not None:
                x, y, w, h = cv2.boundingRect(coords)
                gray = gray[y : y + h, x : x + w]  # Crop exactly to the LCD screen!

            # 3. Scale up the tightly cropped LCD screen by 3x
            gray = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)

            # 4. Now that the white mask is gone, Otsu's thresholding will work flawlessly
            _, binary = cv2.threshold(
                gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
            )

            # 5. Close the LCD 7-segment gaps using Morphology
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            morph = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            morph = cv2.dilate(morph, kernel, iterations=1)

            # 6. Invert back to black text on white background
            final_cv_image = cv2.bitwise_not(morph)

            # 7. Add a solid white padding border (Crucial for Tesseract)
            final_cv_image = cv2.copyMakeBorder(
                final_cv_image,
                40,
                40,
                40,
                40,
                cv2.BORDER_CONSTANT,
                value=[255, 255, 255],
            )
            # Convert to PIL Image for Tesseract
            image = Image.fromarray(final_cv_image)
            if self.save_frame:
                self.write_output_file(image=image, name=filename)
        else:
            raise ValueError("Either 'frame' or 'image_path' must be provided.")

        try:
            # We can get detailed data (bounding boxes, confidence, etc.)
            data = pytesseract.image_to_data(
                image, output_type=pytesseract.Output.DICT, config=config
            )

            # Group by line_num or block_num, or simply use image_to_string for raw text lines
            raw_text = pytesseract.image_to_string(image, config=config)
            print(f"Raw OCR text: {raw_text}")  # Debug print to see raw OCR output

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

            # Also populate word-level bounding boxes if available for draw_text_boxes mimicry
            text_regions = []
            n_boxes = len(data["text"])
            for i in range(n_boxes):
                try:
                    conf = int(data["conf"][i])
                except (ValueError, TypeError):
                    conf = -1
                if conf > 0:  # confidence filter
                    text = data["text"][i].strip()
                    if text:
                        x, y, w, h = (
                            data["left"][i],
                            data["top"][i],
                            data["width"][i],
                            data["height"][i],
                        )
                        # Convert to Azure style bounding box: [x1,y1, x2,y2, x3,y3, x4,y4]
                        bounding_box = [x, y, x + w, y, x + w, y + h, x, y + h]
                        text_regions.append(
                            {"bounding_box": bounding_box, "text": text}
                        )

            # Create list of MockResultPage
            result_pages = [MockResultPage(parsed_lines)]
            return result_pages, text_regions

        except Exception as e:
            logger.error(f"Error processing image with Tesseract: {e}")
            raise e
