from utils.rtsp_client import RTSPClient
from utils.azure_client import AzureClient
from utils.tesseract_client import TesseractClient
from utils.configuration import YamlConfigLoader
from utils.utils import generate_result
from utils.mqtt import MqttCLient
import logging

logger = logging.getLogger("troubleshoot")
configuration = YamlConfigLoader()


def apply_image_pipeline(client_rtsp: RTSPClient, config: YamlConfigLoader) -> dict:
    """Apply all active image processing steps and return a dict of saved frame paths."""
    saved_frames = {}
    img_cfg = config.get_param("rtsp", "image")
    logger.info("Starting image pipeline")

    if bool(img_cfg.get("convert_to_bgr")):
        logger.info("Pipeline step: RGB → BGR conversion")
        client_rtsp.convert_rgb2bgr(filename="2.convert_bgr")
        saved_frames["convert_bgr"] = "2.convert_bgr.jpg"

    if bool(img_cfg.get("convert_to_grey")):
        logger.info("Pipeline step: BGR → Greyscale conversion")
        client_rtsp.convert_bgr2gray(filename="3.convert_grey")
        saved_frames["convert_grey"] = "3.convert_grey.jpg"

    exposure = img_cfg.get("exposure", {})
    if bool(exposure.get("active")):
        logger.info(
            f"Pipeline step: Exposure adjustment in_range={exposure.get('in_range')} out_range={exposure.get('out_range')}"
        )
        client_rtsp.improve_exposure_intensity(
            in_range=tuple(exposure["in_range"]),
            out_range=tuple(exposure["out_range"]),
            filename="4.exposure",
        )
        saved_frames["exposure"] = "4.exposure.jpg"

    contrast = img_cfg.get("contrast", {})
    if bool(contrast.get("active")):
        logger.info(
            f"Pipeline step: Contrast adjustment alpha={contrast.get('alpha')} beta={contrast.get('beta')}"
        )
        client_rtsp.adjust_contrast(
            alpha=contrast["alpha"],
            beta=contrast["beta"],
            filename="5.contrast",
        )
        saved_frames["contrast"] = "5.contrast.jpg"

    sharpen = img_cfg.get("sharpen", {})
    if bool(sharpen.get("active")):
        logger.info(
            f"Pipeline step: Sharpen amount={sharpen.get('amount')} threshold={sharpen.get('threshold')}"
        )
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
        logger.info(
            f"Pipeline step: Crop using key='{coord_key}' coordinates={coordinates}"
        )
        if all(coordinates.get(k) is not None for k in ("x", "y", "width", "height")):
            client_rtsp.crop_image(
                x=int(coordinates["x"]),
                y=int(coordinates["y"]),
                width=int(coordinates["width"]),
                height=int(coordinates["height"]),
                filename="7.crop",
            )
            saved_frames["crop"] = "7.crop.jpg"
            logger.info(
                f"Crop applied: x={coordinates['x']} y={coordinates['y']} w={coordinates['width']} h={coordinates['height']}"
            )
        else:
            logger.warning(
                f"Crop skipped — incomplete coordinates for key '{coord_key}': {coordinates}"
            )

    logger.info(f"Image pipeline completed. Steps applied: {list(saved_frames.keys())}")
    return saved_frames


def create_improved_frame(use_file: bool = False, file=None):
    rtsp_url = None if use_file else configuration.get_param("rtsp", "url")
    client_rtsp = RTSPClient(rtsp_url=rtsp_url)

    default_folder = configuration.get_param("frame", "storage_path")
    client_rtsp.set_default_folder(default_folder=default_folder)
    logger.info(f"Frame storage folder: {default_folder}")

    if use_file:
        if file:
            logger.info(f"Loading frame from uploaded file: {file.filename}")
            client_rtsp.load_frame_from_file(file=file, filename="origine")
        else:
            logger.warning("use_file=True but no file provided")
    else:
        logger.info("Capturing frame from RTSP stream")
        client_rtsp.get_frame(filename="0.frame_origine")

    rotate = configuration.get_param("vision", "rotate")
    logger.info(f"Rotation angle: {rotate}")
    if rotate > 0:
        logger.info(f"Applying rotation: {rotate}°")
        client_rtsp.rotate_frame(angle=rotate, filename="1.rotate")

    pipeline_frames = apply_image_pipeline(client_rtsp, configuration)

    frame_to_process = client_rtsp.improve_frame
    client_rtsp.write_output_file(name="8.frame_final", frame=frame_to_process)
    logger.info("Final frame written as 8.frame_final.jpg")

    return frame_to_process, pipeline_frames


def _draw_boxes(text_regions, frame, default_folder, filename="10.ocr_boxes"):
    """Shared drawing helper — creates a temporary AzureClient just for its draw method."""
    logger.info(f"Drawing {len(text_regions)} OCR bounding boxes onto frame")
    drawer = AzureClient(vision_key="mock", endpoint_url="mock", save_frame=True)
    drawer.default_folder = default_folder
    drawer.draw_text_boxes(
        text_regions=text_regions,
        frame=frame,
        filename=filename,
    )


def service_process(
    increase_cron_count: bool = False, use_file: bool = False, file=None
):
    logger.info("=== service_process START ===")
    frame_to_process, pipeline_frames = create_improved_frame(
        use_file=use_file, file=file
    )
    default_folder = configuration.get_param("frame", "storage_path")
    source_frame_path = f"{default_folder}/0.frame_origine.jpg"

    try:
        engine = configuration.get_param("vision", "engine")
    except Exception:
        engine = "azure"
    logger.info(f"OCR engine selected: {engine}")

    if engine == "tesseract":
        logger.info("Initialising Tesseract OCR client")
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
        logger.info(f"Tesseract config string: {tesseract_config}")

        client_tesseract = TesseractClient(tesseract_cmd=tesseract_cmd)
        client_tesseract.default_folder = default_folder
        logger.info("Running Tesseract OCR on processed frame")
        result_pages, text_regions = client_tesseract.process_image(
            frame=frame_to_process,
            config=tesseract_config,
            filename="9.tesseract_optimized",
        )
        logger.info(
            f"Tesseract returned {len(result_pages)} page(s), {len(text_regions)} region(s)"
        )
        _draw_boxes(text_regions, frame_to_process, default_folder)

        all_lines = [line for page in result_pages for line in page.lines]
        logger.info(f"Tesseract total lines detected: {len(all_lines)}")
        for i, line in enumerate(all_lines):
            logger.debug(f"  Tesseract line[{i}]: '{line.text}'")

        class _MockResult:
            class _Read:
                class _Block:
                    def __init__(self, lines):
                        self.lines = lines

                def __init__(self, lines):
                    self.blocks = [_MockResult._Read._Block(lines)]

            def __init__(self, lines):
                self.read = _MockResult._Read(lines)

        ocr_result = _MockResult(all_lines)

    else:
        logger.info("Initialising Azure Vision OCR client")
        subscription_key = configuration.get_param("vision", "key")
        endpoint = configuration.get_param("vision", "endpoint")
        logger.info(f"Azure endpoint: {endpoint}")

        client_azure = AzureClient(vision_key=subscription_key, endpoint_url=endpoint)
        client_azure.default_folder = default_folder

        logger.info("Sending frame to Azure OCR...")
        ocr_result = client_azure.process_image(frame=frame_to_process)
        logger.info(f"Azure OCR raw result: {ocr_result}")

        text_regions = client_azure.get_regions(result=ocr_result)
        logger.info(f"Azure OCR text regions ({len(text_regions)}): {text_regions}")

        client_azure.draw_text_boxes(
            text_regions=text_regions,
            frame=frame_to_process,
            filename="10.ocr_boxes",
        )

    vision_counter = int(configuration.get_param("vision", "counter"))
    configuration.set_param("vision", "counter", value=vision_counter + 1)
    logger.info(f"Vision counter incremented to: {vision_counter + 1}")

    line_with_data = configuration.get_param("vision", "line_with_data") or 0
    logger.info(f"Line with data index: {line_with_data}")

    read_blocks = ocr_result.read.blocks if ocr_result and ocr_result.read else []
    all_lines = [line for block in read_blocks for line in block.lines]
    logger.info(f"Total OCR lines available: {len(all_lines)}")

    if not all_lines:
        logger.error("OCR returned no lines of text — cannot extract meter value")
        return ValueError("No lines of text were recognized by the OCR engine.")

    raw_result = all_lines[line_with_data].text
    logger.info(f"Raw OCR result (line {line_with_data}): '{raw_result}'")

    try:
        result_values = generate_result(raw_result=raw_result)
        logger.info(f"Parsed result values: {result_values}")
    except Exception as e:
        logger.error(
            f"Error generating result from OCR text '{raw_result}': {e}", exc_info=True
        )
        return ValueError("couldn't get the digitalisation of the meter")

    current_value = float(result_values.get("total_liters"))
    previous_value = configuration.get_param("result", "previous")
    logger.info(f"Meter value — current: {current_value}, previous: {previous_value}")
    if not previous_value:
        configuration.set_param("result", "previous", value=current_value)
        previous_value = current_value
        logger.info(f"First reading — previous value initialised to {current_value}")

    if previous_value > current_value:
        logger.warning(
            f"Value regression detected: previous={previous_value} > current={current_value}"
        )
        return ValueError(
            f"previous value {previous_value} is > to current value {current_value}"
        )
    configuration.set_param("result", "current", value=current_value)
    logger.info(f"Current meter value saved: {current_value}")

    logger.info("Publishing meter values and frame via MQTT")
    client_mqtt = MqttCLient()
    client_mqtt.mqtt_publish_device()
    client_mqtt.send_value(values=result_values)
    logger.info("MQTT value publish complete")

    client_mqtt.send_frame(image_path=source_frame_path)
    logger.info(f"MQTT frame publish complete: {source_frame_path}")

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

    data = {
        "images": {
            "source": source_frame_path,
            "final": f"{default_folder}/8.frame_final.jpg",
            "ocr_boxes": f"{default_folder}/10.ocr_boxes.jpg",
        },
        "pipeline": pipeline_steps,
        "result": result_values,
    }

    if increase_cron_count:
        current_count = int(configuration.get_param("service", "counter"))
        configuration.set_param("service", "counter", value=current_count + 1)
        logger.info(f"Service cron counter incremented to: {current_count + 1}")

    logger.info("=== service_process END ===")
    return data
