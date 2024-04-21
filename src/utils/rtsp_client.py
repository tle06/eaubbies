import cv2
import numpy as np
import skimage.exposure
from pathlib import Path, PurePath
import base64
import time
import logging


class RTSPClient:

    default_folder = "../frames"

    def __init__(self, rtsp_url: str, save_frame: bool = True):
        self.video_url = rtsp_url
        self.save_frame = save_frame

    def write_output_file(self, name: str, frame):
        filename = f"{name}.jpg"
        path_str = f"{self.default_folder}/{filename}"
        fullpath = Path(path_str)
        fullpath.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(fullpath), frame)
        print("Frame saved at", str(fullpath))
        return fullpath

    def set_default_folder(self, default_folder: str):
        self.default_folder = default_folder
        return self.default_folder

    def get_frame(self):
        self.frame = self.get_frame_from_rtsp()
        self.improve_frame = self.frame.copy()
        return self.frame

    def load_frame_from_file(self, file: str):
        self.frame = cv2.imread(file, cv2.IMREAD_COLOR)
        self.improve_frame = self.frame.copy()

        return self.frame

    def load_frame_base64(self, data_url):
        base64_str = data_url.split(",")[1]
        try:
            frame_data = base64.b64decode(base64_str)
            nparr = np.frombuffer(frame_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            self.frame = frame
            self.improve_frame = self.frame.copy()
            return self.frame
        except Exception as e:
            # Handle any exceptions, such as decoding errors
            print("Error decoding base64 data:", e)
            return "Error processing image data"

    def convert_frame_to_jpg(self, frame):
        ret, buffer = cv2.imencode(".jpg", frame)
        result = "data:image/jpeg;base64," + base64.b64encode(buffer).decode()
        return result

    def get_improve_frame(self):
        return self.improve_frame

    def get_frame_from_rtsp(
        self,
    ):
        # Open RTSP stream
        cap = cv2.VideoCapture(self.video_url)
        if not cap.isOpened():
            print("Error: Unable to open RTSP stream.")
            return None
        # Capture the first frame
        ret, frame = cap.read()

        # Check if the frame is captured successfully
        if not ret:
            print("Error: Unable to capture frame.")
            cap.release()
            return None

        if self.save_frame:
            # Save the frame as an image
            self.write_output_file(name="origine", frame=frame)

        # Release the capture object
        cap.release()

        return frame

    def convert_rgb2bgr(self):
        self.improve_frame = cv2.cvtColor(self.improve_frame, cv2.COLOR_RGB2BGR)
        if self.save_frame:
            self.write_output_file(name="frame_rgb2bgr", frame=self.improve_frame)
        return self.improve_frame

    def convert_bgr2gray(self):
        self.improve_frame = cv2.cvtColor(self.improve_frame, cv2.COLOR_BGR2GRAY)
        if self.save_frame:
            self.write_output_file(name="frame_bgr2gray", frame=self.improve_frame)
        return self.improve_frame

    def improve_exposure_intensity(
        self, in_range: tuple = (0, 128), out_range: tuple = (0, 255)
    ):
        self.improve_frame = skimage.exposure.rescale_intensity(
            self.improve_frame, in_range=in_range, out_range=out_range
        )
        if self.save_frame:
            self.write_output_file(
                name="frame_exposure_intensity", frame=self.improve_frame
            )
        return self.improve_frame

    def add_gaussian_blur(self):
        self.improve_frame = cv2.GaussianBlur(self.improve_frame, (5, 5), 0)
        if self.save_frame:
            self.write_output_file(name="frame_gaussian_blur", frame=self.improve_frame)
        return self.improve_frame

    def adaptive_threshold(self):
        self.improve_frame = cv2.adaptiveThreshold(
            self.improve_frame,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            11,
            2,
        )
        if self.save_frame:
            self.write_output_file(
                name="frame_adaptive_threshold", frame=self.improve_frame
            )
        return self.improve_frame

    def improve_morphology(self):
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        self.improve_frame = cv2.morphologyEx(
            self.improve_frame, cv2.MORPH_CLOSE, kernel
        )

        if self.save_frame:
            self.write_output_file(name="frame_morphology", frame=self.improve_frame)
        return self.improve_frame

    def add_brightness(self, brightness_factor: int):

        brightness_min = 0
        dtype = np.uint8
        brightness_max = np.iinfo(dtype).max

        if brightness_factor < brightness_min:
            brightness_factor = brightness_min
            print(
                f"brightness_factor is < of min ({brightness_min}), so min value will be used"
            )

        if brightness_factor > brightness_max:
            brightness_factor = brightness_max
            print(
                f"brightness_factor is > of max ({brightness_max}), so max value will be used"
            )

        self.improve_frame = cv2.add(self.improve_frame, np.array([brightness_factor]))
        if self.save_frame:
            self.write_output_file(name="frame_brightness,frame=self.improve_frame")
        return self.improve_frame

    def add_exposure(
        self,
        exposure_factor: int,
    ):

        exposure_min = 0
        exposure_max = float("inf")

        if exposure_factor < exposure_min:
            exposure_factor = exposure_min
            print(
                f"exposure_factor is < of min ({exposure_min}), so min value will be used"
            )

        if exposure_factor > exposure_max:
            exposure_factor = exposure_max
            print(
                f"exposure_factor is > of max ({exposure_max}), so max value will be used"
            )

        self.improve_frame = cv2.add(self.improve_frame, np.array([exposure_factor]))
        if self.save_frame:
            self.write_output_file(name="frame_exposure,frame=self.improve_frame")
        return self.improve_frame

    def get_stream(self):
        cap = cv2.VideoCapture(self.video_url)
        while True:
            start_time = time.time()
            success, frame = cap.read()
            if not success:
                break
            # Encode frame as JPEG before streaming
            ret, buffer = cv2.imencode(".jpg", frame)
            frame = buffer.tobytes()
            yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
            elapsed_time = time.time() - start_time
            logging.debug(f"Frame generation time: {elapsed_time} seconds")
