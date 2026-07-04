from utils.rtsp_client import RTSPClient
from utils.azure_client import AzureClient
from utils.tesseract_client import TesseractClient
from utils.configuration import YamlConfigLoader
from utils.utils import generate_result
from utils.mqtt import MqttCLient
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("troubleshoot")
configuration = YamlConfigLoader()


def apply_image_pipeline(client_rtsp: RTSPClient, config: YamlConfigLoader) -> dict:
    """Apply all active image processing steps and return a dict of saved frame paths."""
    saved_frames = {}
    img_cfg = config.get_param("rtsp", "image")

    if bool(img_cfg.get("convert_to_bgr")):
        client_rtsp.convert_rgb2bgr(filename="2.convert_bgr")
        saved_frames["convert_bgr"] = "2.convert_bgr.jpg"

    if bool(img_cfg.get("convert_to_grey")):
        client_rtsp.convert_bgr2gray(filename="3.convert_grey")
        saved_frames["convert_grey"] = "3.convert_grey.jpg"

    exposure = img_cfg.get("exposure", {})
    if bool(exposure.get("active")):
        client_rtsp.improve_exposure_intensity(
            in_range=tuple(exposure["in_range"]),
            out_range=tuple(exposure["out_range"]),
            filename="4.exposure",
        )
        saved_frames["exposure"] = "4.exposure.jpg"

    contrast = img_cfg.get("contrast", {})
    if bool(contrast.get("active")):
        client_rtsp.adjust_contrast(
            alpha=contrast["alpha"],
            beta=contrast["beta"],
            filename="5.contrast",
        )
        saved_frames["contrast"] = "5.contrast.jpg"

    sharpen = img_cfg.get("sharpen", {})
    if bool(sharpen.get("active")):
        client_rtsp.sharpen_image(
            amount=sharpen["amount"],
            threshold=sharpen["threshold"],
            filename="6.sharpen",
        )
        saved_frames["sharpen"] = "6.sharpen.jpg"

    crop = img_cfg.get("crop_image", {})
    if bool(crop.get("active")):
        coord_key = crop.get("coordinates", "integer").lower().strip()
        coordinates = config.get_param("vision", "coordinates", coord_key)
        logger.info(f"Crop using '{coord_key}': {coordinates}")
        if all(coordinates.get(k) is not None for k in ("x", "y", "width", "height")):
            client_rtsp.crop_image(
                x=int(coordinates["x"]),
                y=int(coordinates["y"]),
                width=int(coordinates["width"]),
                height=int(coordinates["height"]),
                filename="7.crop",
            )
            saved_frames["crop"] = "7.crop.jpg"

    return saved_frames


def create_improved_frame(use_file: bool = False, file=None):
    rtsp_url = None if use_file else configuration.get_param("rtsp", "url")
    client_rtsp = RTSPClient(rtsp_url=rtsp_url)

    default_folder = configuration.get_param("frame", "storage_path")
    client_rtsp.set_default_folder(default_folder=default_folder)

    if use_file:
        if file:
            logger.info(file.filename)
            client_rtsp.load_frame_from_file(file=file, filename="origine")
    else:
        client_rtsp.get_frame(filename="0.frame_origine")

    rotate = configuration.get_param("vision", "rotate")
    logger.info(f"rotate: {rotate}")
    if rotate > 0:
        logger.info(f"rotate image to {rotate} degrees")
        client_rtsp.rotate_frame(angle=rotate, filename="1.rotate")

    pipeline_frames = apply_image_pipeline(client_rtsp, configuration)

    frame_to_process = client_rtsp.improve_frame
    client_rtsp.write_output_file(name="8.frame_final", frame=frame_to_process)

    return frame_to_process, pipeline_frames


def service_process(
    increase_cron_count: bool = False, use_file: bool = False, file=None
):
    frame_to_process, pipeline_frames = create_improved_frame(use_file=use_file, file=file)
    default_folder = configuration.get_param("frame", "storage_path")

    try:
        engine = configuration.get_param("vision", "engine")
    except Exception:
        engine = "azure"

    if engine == "tesseract":
        tesseract_cmd = None
        try:
            tesseract_cmd = configuration.get_param("vision", "tesseract_cmd")
        except Exception:
            pass
        tesseract_config = "--psm 8 -c tessedit_char_whitelist=0123456789"
        try:
            tesseract_config = configuration.get_param("vision", "tesseract_config")
        except Exception:
            pass

        client_tesseract = TesseractClient(tesseract_cmd=tesseract_cmd)
        result, text_regions = client_tesseract.process_image(
            frame=frame_to_process,
            config=tesseract_config,
            filename="9.tesseract_optimized",
        )
        # reuse azure draw helper for consistent rendering
        client_azure = AzureClient(vision_key="mock", endpoint_url="mock", save_frame=True)
        client_azure.default_folder = default_folder
        client_azure.draw_text_boxes(
            text_regions=text_regions,
            frame=frame_to_process,
            filename="10.ocr_boxes",
        )
    else:
        logger.info("Using Azure OCR Engine")
        subscription_key = configuration.get_param("vision", "key")
        endpoint = configuration.get_param("vision", "endpoint")

        client_azure = AzureClient(vision_key=subscription_key, endpoint_url=endpoint)
        client_azure.default_folder = default_folder

        result = client_azure.process_image(frame=frame_to_process)
        logger.info(f"Azure OCR Result: {result}")

        text_regions = client_azure.get_regions(result=result)
        logger.info(f"Azure OCR Text Regions: {text_regions}")

        client_azure.draw_text_boxes(
            text_regions=text_regions,
            frame=frame_to_process,
            filename="10.ocr_boxes",
        )

    vision_counter = int(configuration.get_param("vision", "counter"))
    configuration.set_param("vision", "counter", value=vision_counter + 1)

    line_with_data = configuration.get_param("vision", "line_with_data") or 0
    logger.info(f"Line with data: {line_with_data}")

    read_blocks = result.read.blocks if result and result.read else []
    all_lines = [line for block in read_blocks for line in block.lines]

    if not all_lines:
        return ValueError("No lines of text were recognized by the OCR engine.")

    raw_result = all_lines[line_with_data].text
    logger.info(f"Raw OCR result: {raw_result}")

    try:
        result_values = generate_result(raw_result=raw_result)
    except Exception as e:
        logger.error(f"Error generating result from OCR text: {e}")
        return ValueError("couldn't get the digitalisation of the meter")

    current_value = float(result_values.get("total_liters"))
    previous_value = configuration.get_param("result", "previous")
    if not previous_value:
        configuration.set_param("result", "previous", value=current_value)
        previous_value = current_value

    if previous_value > current_value:
        return ValueError(
            f"previous value {previous_value} is > to current value {current_value}"
        )
    configuration.set_param("result", "current", value=current_value)

    client_mqtt = MqttCLient()
    client_mqtt.mqtt_publish_device()
    client_mqtt.send_value(values=result_values)

    # Build image map: static pipeline frames + final + ocr
    images = {"source": f"{default_folder}/0.frame_origine.jpg"}
    step_labels = {
        "convert_bgr": "BGR Convert",
        "convert_grey": "Greyscale",
        "exposure": "Exposure",
        "contrast": "Contrast",
        "sharpen": "Sharpen",
        "crop": "Crop",
    }
    pipeline_steps = [
        {"label": step_labels.get(k, k), "path": f"{default_folder}/{v}"}
        for k, v in pipeline_frames.items()
    ]
    images["final"] = f"{default_folder}/8.frame_final.jpg"
    images["ocr_boxes"] = f"{default_folder}/10.ocr_boxes.jpg"

    data = {
        "images": images,
        "pipeline": pipeline_steps,
        "result": result_values,
    }

    if increase_cron_count:
        current_count = int(configuration.get_param("service", "counter"))
        configuration.set_param("service", "counter", value=current_count + 1)

    return data
