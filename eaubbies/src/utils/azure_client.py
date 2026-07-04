from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures
from azure.core.credentials import AzureKeyCredential
import io, cv2
import numpy as np
from pathlib import Path


class AzureClient:
    def __init__(self, vision_key: str, endpoint_url: str, save_frame: bool = True):
        self.save_frame = save_frame
        self.default_folder = "../frames"
        # Only build the real client when we have valid credentials
        if vision_key and vision_key != "mock" and endpoint_url and endpoint_url != "mock":
            self.client = ImageAnalysisClient(
                endpoint=endpoint_url,
                credential=AzureKeyCredential(vision_key)
            )
        else:
            self.client = None

    # ── I/O helper ────────────────────────────────────────────────────────────
    def write_output_file(self, name: str, frame):
        filename = f"{name}.jpg"
        path_str = f"{self.default_folder}/{filename}"
        fullpath = Path(path_str)
        fullpath.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(fullpath), frame)
        return fullpath

    # ── OCR ───────────────────────────────────────────────────────────────────
    def process_image(self, frame=None, image_path: str = None, image_url: str = None):
        if self.client is None:
            raise ValueError("AzureClient was initialised without valid credentials.")

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
            stream.seek(0)
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

    # ── Drawing ───────────────────────────────────────────────────────────────
    def draw_text_boxes(
        self,
        text_regions: list,
        frame,
        filename: str = "ocr_boxes",
    ):
        """
        Draw bounding polygons + text labels on a copy of *frame* and save it.

        text_regions format (same for Azure and Tesseract paths):
            [{"bounding_box": [x1,y1, x2,y2, x3,y3, x4,y4], "text": "..."}]
        """
        # Work on a uint8 BGR copy so cv2 drawing always works regardless of
        # greyscale / float frames produced by the pipeline.
        if len(frame.shape) == 2 or frame.shape[2] == 1:
            annotated = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        else:
            annotated = frame.copy()

        if annotated.dtype != np.uint8:
            annotated = np.clip(annotated, 0, 255).astype(np.uint8)

        for region in text_regions:
            bb = region.get("bounding_box", [])
            text = region.get("text", "")

            if len(bb) >= 8:
                pts = np.array(
                    [[int(bb[i]), int(bb[i + 1])] for i in range(0, 8, 2)],
                    dtype=np.int32,
                )
                cv2.polylines(annotated, [pts], isClosed=True, color=(0, 255, 0), thickness=2)
                cv2.putText(
                    annotated,
                    text,
                    (pts[0][0], pts[0][1] - 6),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (0, 255, 0),
                    1,
                    cv2.LINE_AA,
                )

        if self.save_frame:
            self.write_output_file(name=filename, frame=annotated)

        return annotated
