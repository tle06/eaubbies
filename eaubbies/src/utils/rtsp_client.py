import cv2
import numpy as np
import skimage.exposure
from pathlib import Path
import base64
import time
import logging

logger = logging.getLogger(__name__)


class RTSPClient:
    """
    Capture frames from an RTSP stream (or file/base64) and apply a chain of
    OpenCV / scikit-image enhancement operations, persisting intermediate
    frames for debugging and the web UI.
    """

    default_folder = "../frames"

    def __init__(self, rtsp_url: str = None, save_frame: bool = True):
        """
        Parameters:
            rtsp_url (str): RTSP stream URL. May be None when frames are loaded
                from an uploaded file instead.
            save_frame (bool): When True, each processing step writes its result
                to ``default_folder``.
        """
        self.video_url = rtsp_url
        self.save_frame = save_frame

    def write_output_file(self, name: str, frame):
        """Write *frame* as ``<name>.jpg`` in ``default_folder`` and return its path."""
        filename = f"{name}.jpg"
        path_str = f"{self.default_folder}/{filename}"
        fullpath = Path(path_str)
        fullpath.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(fullpath), frame)
        logger.info(f"Frame saved at {str(fullpath)}")
        return fullpath

    def set_default_folder(self, default_folder: str):
        """Set the folder where processed frames are written."""
        self.default_folder = default_folder
        return self.default_folder

    def get_frame(self, filename: str = "origine"):
        """Capture a frame from the RTSP stream and seed ``improve_frame``."""
        self.frame = self.get_frame_from_rtsp(filename=filename)
        self.improve_frame = self.frame.copy()
        if self.save_frame:
            self.write_output_file(name=filename, frame=self.frame)
        return self.frame

    def load_frame_from_file(self, file: str, filename: str = "origine"):
        """Decode an uploaded image *file* into a frame and seed ``improve_frame``."""
        file_bytes = file.read()
        np_array = np.frombuffer(file_bytes, np.uint8)
        self.frame = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
        if self.save_frame:
            self.write_output_file(name=filename, frame=self.frame)
        self.improve_frame = self.frame.copy()
        return self.frame

    def load_frame_base64(self, data_url):
        """Decode a ``data:`` base64 image URL into a frame."""
        base64_str = data_url.split(",")[1]
        try:
            frame_data = base64.b64decode(base64_str)
            nparr = np.frombuffer(frame_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            self.frame = frame
            self.improve_frame = self.frame.copy()
            return self.frame
        except Exception as e:
            logger.error(f"Error decoding base64 data: {e}")
            return "Error processing image data"

    def convert_frame_to_jpg(self, frame):
        """Encode *frame* as a base64 JPEG ``data:`` URL string."""
        ret, buffer = cv2.imencode(".jpg", frame)
        result = "data:image/jpeg;base64," + base64.b64encode(buffer).decode()
        return result

    def get_improve_frame(self):
        """Return the current in-progress (improved) frame."""
        return self.improve_frame

    def get_frame_from_rtsp(
        self,
        filename: str = "origine",
    ):
        """Open the RTSP stream, grab a single frame and return it (or None on failure)."""
        if self.video_url:
            logger.info(f"Attempting to open RTSP stream: {self.video_url}")
            cap = cv2.VideoCapture(self.video_url)
            if not cap.isOpened():
                logger.error("Unable to open RTSP stream: %s", self.video_url)
                return None
            ret, frame = cap.read()
            if not ret:
                logger.error(
                    "Unable to capture frame from RTSP stream: %s", self.video_url
                )
                cap.release()
                return None
            if self.save_frame:
                self.write_output_file(name=filename, frame=frame)
            cap.release()
            return frame
        raise ValueError("No rtsp URL")

    def convert_rgb2bgr(self, filename: str = "frame_rgb2bgr"):
        """Convert the working frame from RGB to BGR."""
        self.improve_frame = cv2.cvtColor(self.improve_frame, cv2.COLOR_RGB2BGR)
        if self.save_frame:
            self.write_output_file(name=filename, frame=self.improve_frame)
        return self.improve_frame

    def convert_bgr2gray(self, filename: str = "frame_bgr2gray"):
        """Convert the working frame from BGR to greyscale."""
        self.improve_frame = cv2.cvtColor(self.improve_frame, cv2.COLOR_BGR2GRAY)
        if self.save_frame:
            self.write_output_file(name=filename, frame=self.improve_frame)
        return self.improve_frame

    def improve_exposure_intensity(
        self,
        in_range: tuple = (0, 128),
        out_range: tuple = (0, 255),
        filename: str = "frame_exposure_intensity",
    ):
        """Rescale pixel intensity (scikit-image) to stretch contrast/exposure."""
        self.improve_frame = skimage.exposure.rescale_intensity(
            self.improve_frame, in_range=in_range, out_range=out_range
        )
        if (
            self.improve_frame.dtype == np.float64
            or self.improve_frame.dtype == np.float32
        ):
            self.improve_frame = (
                (self.improve_frame * 255).astype(np.uint8)
                if self.improve_frame.max() <= 1.0
                else self.improve_frame.astype(np.uint8)
            )
        if self.save_frame:
            self.write_output_file(name=filename, frame=self.improve_frame)
        return self.improve_frame

    def add_gaussian_blur(self, filename: str = "frame_gaussian_blur"):
        """Apply a 5x5 Gaussian blur to the working frame."""
        self.improve_frame = cv2.GaussianBlur(self.improve_frame, (5, 5), 0)
        if self.save_frame:
            self.write_output_file(name=filename, frame=self.improve_frame)
        return self.improve_frame

    def adaptive_threshold(self, filename: str = "frame_adaptive_threshold"):
        """Apply Gaussian adaptive inverse thresholding (expects greyscale input)."""
        self.improve_frame = cv2.adaptiveThreshold(
            self.improve_frame,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            11,
            2,
        )
        if self.save_frame:
            self.write_output_file(name=filename, frame=self.improve_frame)
        return self.improve_frame

    def improve_morphology(self, filename: str = "frame_morphology"):
        """Apply a morphological close to fill small gaps in the digits."""
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        self.improve_frame = cv2.morphologyEx(
            self.improve_frame, cv2.MORPH_CLOSE, kernel
        )
        if self.save_frame:
            self.write_output_file(name=filename, frame=self.improve_frame)
        return self.improve_frame

    def adjust_brightness(self, factor: int, filename="frame_brightness"):
        """Add a clamped brightness *factor* to every pixel."""
        factor = max(0, min(255, factor))
        self.improve_frame = cv2.add(self.improve_frame, np.array([factor]))
        if self.save_frame:
            self.write_output_file(name=filename, frame=self.improve_frame)
        return self.improve_frame

    def get_stream(self):
        """Yield MJPEG multipart chunks from the RTSP stream (used by the UI)."""
        cap = cv2.VideoCapture(self.video_url)
        while True:
            start_time = time.time()
            success, frame = cap.read()
            if not success:
                logger.warning("Video stream ended or frame could not be read")
                break
            ret, buffer = cv2.imencode(".jpg", frame)
            frame = buffer.tobytes()
            yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
            elapsed_time = time.time() - start_time
            logger.debug(f"Frame generation time: {elapsed_time:.3f}s")

    def crop_image(self, x, y, width, height, filename="frame_cropped"):
        """Crop the working frame to the given rectangle."""
        self.improve_frame = self.improve_frame[y : y + height, x : x + width]
        if self.save_frame:
            self.write_output_file(name=filename, frame=self.improve_frame)
        return self.improve_frame

    def join_images_with_dot(self, image1, image2, filename: str = "frame_join"):
        """Concatenate two images side by side separated by a drawn dot."""
        if image1 is None or image2 is None:
            logger.error("Both images are required for join_images_with_dot")
            return None
        max_height = max(image1.shape[0], image2.shape[0])
        image1 = cv2.resize(
            image1, (int(image1.shape[1] * (max_height / image1.shape[0])), max_height)
        )
        image2 = cv2.resize(
            image2, (int(image2.shape[1] * (max_height / image2.shape[0])), max_height)
        )
        dot_height = max_height
        dot_width = 20
        dot = np.ones((dot_height, dot_width, 3), dtype=np.uint8) * 255
        cv2.putText(
            dot,
            ".",
            (2, int(dot_height / 2) + 6),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 0, 0),
            2,
        )
        joined_image = np.concatenate((image1, dot, image2), axis=1)
        if self.save_frame:
            self.write_output_file(name=filename, frame=joined_image)
        return joined_image

    def adjust_contrast(self, alpha, beta, filename: str = "frame_contrast"):
        """Linearly scale contrast (*alpha*) and brightness (*beta*)."""
        self.improve_frame = cv2.convertScaleAbs(
            self.improve_frame, alpha=alpha, beta=beta
        )
        if self.save_frame:
            self.write_output_file(name=filename, frame=self.improve_frame)
        return self.improve_frame

    def sharpen_image(self, amount=1.0, threshold=0, filename: str = "frame_sharpened"):
        """Apply unsharp masking to sharpen the working frame."""
        blurred = cv2.GaussianBlur(self.improve_frame, (0, 0), 3)
        sharpened = cv2.addWeighted(
            self.improve_frame, 1.0 + amount, blurred, -amount, 0
        )
        self.improve_frame = np.clip(sharpened, 0, 255)
        if self.save_frame:
            self.write_output_file(name=filename, frame=self.improve_frame)
        return self.improve_frame

    def deconvolution(self, kernel, iterations=10, filename: str = "frame_deconvolved"):
        """Richardson-Lucy deconvolution to reverse motion blur (uses *kernel*)."""
        kernel = kernel / np.sum(kernel)
        self.improve_frame = cv2.deconvolutionRL(
            self.improve_frame, kernel, iterations=iterations
        )
        if self.save_frame:
            self.write_output_file(name=filename, frame=self.improve_frame)
        return self.improve_frame

    def motion_blur_kernel(self, kernel_size, angle):
        """Build a directional motion-blur kernel of *kernel_size* at *angle* degrees."""
        angle_rad = np.radians(angle)
        kernel = np.zeros((kernel_size, kernel_size))
        center = (kernel_size - 1) / 2
        for i in range(kernel_size):
            for j in range(kernel_size):
                x = i - center
                y = j - center
                if np.abs(np.sin(angle_rad) * x - np.cos(angle_rad) * y) < center:
                    kernel[i, j] = 1.0 / kernel_size
        return kernel

    def upscale_image(
        self, scale_factor: float = 2.0, filename: str = "frame_upscaled"
    ):
        """Bicubically upscale the working frame by *scale_factor*."""
        if self.improve_frame is None:
            logger.warning("upscale_image called but improve_frame is None")
            return None
        width = int(self.improve_frame.shape[1] * scale_factor)
        height = int(self.improve_frame.shape[0] * scale_factor)
        self.improve_frame = cv2.resize(
            self.improve_frame, (width, height), interpolation=cv2.INTER_CUBIC
        )
        logger.info(f"Image upscaled by {scale_factor}x to {width}x{height}")
        if self.save_frame:
            self.write_output_file(name=filename, frame=self.improve_frame)
        return self.improve_frame

    def rotate_frame(self, angle: float = 0.0, filename: str = "frame_rotated"):
        """Rotate the working frame by *angle* degrees, expanding the canvas to fit."""
        height, width = self.improve_frame.shape[:2]
        cX, cY = width / 2.0, height / 2.0
        rotation_matrix = cv2.getRotationMatrix2D((cX, cY), angle, 1.0)
        cos = np.abs(rotation_matrix[0, 0])
        sin = np.abs(rotation_matrix[0, 1])
        new_width = int((height * sin) + (width * cos))
        new_height = int((height * cos) + (width * sin))
        rotation_matrix[0, 2] += (new_width / 2.0) - cX
        rotation_matrix[1, 2] += (new_height / 2.0) - cY
        rotated_image = cv2.warpAffine(
            self.improve_frame, rotation_matrix, (new_width, new_height)
        )
        self.improve_frame = rotated_image
        logger.info(f"Frame rotated by {angle}° → new size {new_width}x{new_height}")
        if self.save_frame:
            self.write_output_file(name=filename, frame=self.improve_frame)
        return self.improve_frame
