# https://learn.microsoft.com/en-us/azure/ai-services/computer-vision/quickstarts-sdk/client-library?tabs=linux%2Cvisual-studio&pivots=programming-language-python
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
from azure.cognitiveservices.vision.computervision.models import VisualFeatureTypes
from msrest.authentication import CognitiveServicesCredentials
import io
import cv2
import time
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from pathlib import Path


class AzureClient:
    endpoint = None
    client = None
    subscription_key = None
    default_folder = "../frames"

    def __init__(self, vision_key: str, endpoint_url: str):

        self.subscription_key = vision_key
        self.endpoint = endpoint_url
        self.client = self.authentication()

    def authentication(self):
        client = ComputerVisionClient(
            self.endpoint, CognitiveServicesCredentials(self.subscription_key)
        )
        return client

    def verify_credentials(self):
        try:
            result = self.process_image(
                image_url="https://learn.microsoft.com/azure/ai-services/computer-vision/media/quickstarts/presentation.png"
            )
            # If the operation was successful, and you received a result object
            if result:
                print("Credentials verified successfully.")
                return True
            else:
                print("Error verifying credentials: Unexpected response.")
                return False
        except Exception as e:
            print("Error verifying credentials:", str(e))
            return False

    def process_image(
        self,
        frame=None,
        image_path: str = None,
        image_url: str = None,
        mode: str = "Printed",
        raw: bool = True,
    ):

        result = None

        if image_path:
            with open(image_path, "rb") as image_stream:
                read_response = self.client.read_in_stream(
                    image=image_stream, mode=mode, raw=raw
                )
        elif image_url:
            read_response = self.client.read(url=image_url, raw=raw)
        elif frame is not None:
            # Convert the frame to bytes
            _, image_bytes = cv2.imencode(".jpg", frame)
            # Convert bytes to stream
            image_stream = io.BytesIO(image_bytes.tobytes())
            read_response = self.client.read_in_stream(
                image=image_stream, mode=mode, raw=raw
            )
        else:
            raise ValueError("Either 'frame' or 'image_path' must be provided.")

        read_operation_location = read_response.headers["Operation-Location"]
        operation_id = read_operation_location.split("/")[-1]

        while True:
            read_result = self.client.get_read_result(operation_id)
            if read_result.status not in ["notStarted", "running"]:
                break
            time.sleep(1)

        if read_result.status == OperationStatusCodes.succeeded:
            result = read_result.analyze_result.read_results

        return result

    def draw_text_boxes(
        self,
        text_regions,
        frame=None,
        image_path: str = None,
        output_image_name: str = "result",
        text_color: str = "red",
        font_size: int = 24,
    ):

        if image_path:
            image = Image.open(image_path)

        elif frame is not None:
            image = Image.fromarray(frame.astype(np.uint8))
        else:
            raise ValueError("Either 'frame' or 'image_path' must be provided.")

        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default().font_variant(size=font_size)

        for region in text_regions:
            bounding_box = region["bounding_box"]
            text = region["text"]
            # Convert bounding box to tuples of (x, y)
            bounding_box = [
                (bounding_box[i], bounding_box[i + 1])
                for i in range(0, len(bounding_box), 2)
            ]
            # Draw rectangle around the text
            draw.polygon(bounding_box, outline=text_color)
            # Print text on the image
            draw.text(
                (bounding_box[0][0], bounding_box[0][1] - 20),
                text,
                fill=text_color,
                font=font,
            )

        filename = f"{output_image_name}.jpg"
        path_str = f"{self.default_folder}/{filename}"
        fullpath = Path(path_str)
        fullpath.parent.mkdir(parents=True, exist_ok=True)
        image.save(str(fullpath))
        print("Frame saved at", str(fullpath))

        return draw

    def get_regions(self, result):
        text_regions = []
        for r in result:
            for l in r.lines:
                text_regions.append({"bounding_box": l.bounding_box, "text": l.text})
        return text_regions
