import cv2
import numpy as np
import skimage.exposure
from pathlib import Path, PurePath
import base64
import time
import logging


class RTSPClient:

    default_folder = "../frames"

    def __init__(self, rtsp_url: str = None, save_frame: bool = True):
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

    def load_frame_from_file(self, file: str, filename: str = "file_origine"):
        file_bytes = file.read()
        np_array = np.frombuffer(file_bytes, np.uint8)
        self.frame = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
        if self.save_frame:
            self.write_output_file(name=filename, frame=self.frame)
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
        if self.video_url:
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
        raise ValueError("No rtsp URL")

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

    def add_brightness(self, brightness_factor: int, filename="frame_brightness"):

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
            self.write_output_file(
                name=filename,
                frame=self.improve_frame,
            )
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
            self.write_output_file(name="frame_exposure", frame=self.improve_frame)
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

    def crop_image(
        self, x: int, y: int, width: int, height: int, filename: str = "frame_cropped"
    ):
        """
        Crop the current frame.

        Parameters:
            x (int): x-coordinate of the top-left corner of the crop rectangle.
            y (int): y-coordinate of the top-left corner of the crop rectangle.
            width (int): Width of the crop rectangle.
            height (int): Height of the crop rectangle.

        Returns:
            numpy.ndarray: Cropped image.
        """
        if self.frame is None:
            print("Error: No frame available to crop.")
            return None
        cropped_frame = self.frame[y : y + height, x : x + width]

        if self.save_frame:
            self.write_output_file(name=filename, frame=cropped_frame)

        return cropped_frame

    def join_images_with_dot(self, image1, image2, filename: str = "frame_join"):
        """
        Join two images together with a dot in between them.

        Parameters:
            image1 (numpy.ndarray): First image.
            image2 (numpy.ndarray): Second image.

        Returns:
            numpy.ndarray: Joined image.
        """
        if image1 is None or image2 is None:
            print("Error: Both images are required for joining.")
            return None

        # Resize both images to have the same height
        max_height = max(image1.shape[0], image2.shape[0])
        image1 = cv2.resize(
            image1, (int(image1.shape[1] * (max_height / image1.shape[0])), max_height)
        )
        image2 = cv2.resize(
            image2, (int(image2.shape[1] * (max_height / image2.shape[0])), max_height)
        )
        # Create an image containing the period character
        dot_height = max_height
        dot_width = 20  # Width of the dot image
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
        """
        Adjust the contrast of the frame.

        Parameters:
            frame (numpy.ndarray): Input frame.
            alpha (float): Contrast control (1.0 - 3.0).
            beta (int): Brightness control (0 - 100).

        Returns:
            numpy.ndarray: Frame with adjusted contrast.
        """
        self.improve_frame = cv2.convertScaleAbs(
            self.improve_frame, alpha=alpha, beta=beta
        )

        if self.save_frame:
            self.write_output_file(name=filename, frame=self.improve_frame)

        return self.improve_frame

    def sharpen_image(self, amount=1.0, threshold=0, filename: str = "frame_sharpened"):
        """
        Sharpen the image using unsharp masking.

        Parameters:
            frame (numpy.ndarray): Input image frame.
            amount (float): Sharpening strength (default: 1.0).
            threshold (int): Threshold for edge detection (default: 0).

        Returns:
            numpy.ndarray: Sharpened image.
        """
        blurred = cv2.GaussianBlur(self.improve_frame, (0, 0), 3)
        sharpened = cv2.addWeighted(
            self.improve_frame, 1.0 + amount, blurred, -amount, 0
        )
        self.improve_frame = np.clip(sharpened, 0, 255)

        if self.save_frame:
            self.write_output_file(name=filename, frame=self.improve_frame)

        return self.improve_frame

    def deconvolution(self, kernel, iterations=10, filename: str = "frame_deconvolved"):
        """
        Perform Richardson-Lucy deconvolution on the blurred image.

        Parameters:
            blurred_image (numpy.ndarray): Blurred input image.
            kernel (numpy.ndarray): Point spread function (PSF) or blur kernel.
            iterations (int): Number of iterations for Richardson-Lucy algorithm (default: 10).

        Returns:
            numpy.ndarray: Deconvolved image.
        """
        # Normalize the kernel
        kernel = kernel / np.sum(kernel)

        # Perform deconvolution using Richardson-Lucy algorithm
        self.improve_frame = cv2.deconvolutionRL(
            self.improve_frame, kernel, iterations=iterations
        )

        if self.save_frame:
            self.write_output_file(name=filename, frame=self.improve_frame)

        return self.improve_frame

    def motion_blur_kernel(self, kernel_size, angle):
        """
        Generate a motion blur kernel.

        Parameters:
            kernel_size (int): Size of the kernel (odd integer).
            angle (float): Angle of motion blur in degrees.

        Returns:
            numpy.ndarray: Motion blur kernel.
        """
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

    def fill_image_except_rectangle(self, x, y, width, height, filename="frame_filled"):
        """
        Fill the image with white color except for a specified rectangle.

        Parameters:
            image (numpy.ndarray): Input image.
            x (int): x-coordinate of the top-left corner of the rectangle.
            y (int): y-coordinate of the top-left corner of the rectangle.
            width (int): Width of the rectangle.
            height (int): Height of the rectangle.

        Returns:
            numpy.ndarray: Image with filled white color except for the specified rectangle.
        """
        filled_image = np.full_like(
            self.improve_frame, 255
        )  # Fill the entire image with white color

        self.write_output_file(name=f"{filename}_1", frame=filled_image)
        # Retain the original pixel values within the specified rectangle
        filled_image[y : y + height, x : x + width] = self.improve_frame[
            y : y + height, x : x + width
        ]
        self.write_output_file(name=f"{filename}_2", frame=filled_image)
        self.improve_frame = filled_image

        if self.save_frame:
            self.write_output_file(name=filename, frame=self.improve_frame)

        return self.improve_frame

    def rotate_frame(self, angle: float = 0.0, filename: str = "frame_rotated"):
        """
        Rotate the frame by a specified angle.

        Parameters:
            frame (numpy.ndarray): Input frame.
            angle (float): Angle of rotation in degrees.

        Returns:
            numpy.ndarray: Rotated frame.
        """
        # Get the height and width of the frame
        height, width = self.improve_frame.shape[:2]
        # Calculate the rotation matrix
        rotation_matrix = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1.0)
        # Apply the rotation matrix to the frame
        rotated_image = cv2.warpAffine(
            self.improve_frame, rotation_matrix, (width, height)
        )
        self.improve_frame = rotated_image

        if self.save_frame:
            self.write_output_file(name=filename, frame=self.improve_frame)

        return self.improve_frame
