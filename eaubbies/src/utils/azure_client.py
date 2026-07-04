from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures
from azure.core.credentials import AzureKeyCredential
import io, cv2

class AzureClient:
    def __init__(self, vision_key: str, endpoint_url: str, save_frame: bool = True):
        self.client = ImageAnalysisClient(
            endpoint=endpoint_url,
            credential=AzureKeyCredential(vision_key)
        )
        self.save_frame = save_frame

    def process_image(self, frame=None, image_path: str = None, image_url: str = None):
        if image_path:
            with open(image_path, "rb") as f:
                image_data = f.read()
            result = self.client.analyze(
                image_data=image_data,
                visual_features=[VisualFeatures.READ]
            )
        elif image_url:
            result = self.client.analyze_from_url(
                image_url=image_url,
                visual_features=[VisualFeatures.READ]
            )
        elif frame is not None:
            _, buf = cv2.imencode(".jpg", frame)
            stream = io.BytesIO(buf.tobytes())
            stream.seek(0)  # Critical: reset before sending
            result = self.client.analyze(
                image_data=stream.read(),
                visual_features=[VisualFeatures.READ]
            )
        else:
            raise ValueError("frame, image_path, or image_url must be provided")
        return result

    def get_regions(self, result):
        regions = []
        if result is None or result.read is None:
            return regions
        for block in result.read.blocks:
            for line in block.lines:
                regions.append({
                    "bounding_box": [pt for p in line.bounding_polygon for pt in (p.x, p.y)],
                    "text": line.text
                })
        return regions