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


def create_improved_frame(use_file: bool = False, file=None):
    # init rtsp client
    rtsp_url = None
    if not use_file:
        rtsp_url = configuration.get_param("rtsp", "url")
    client_rtsp = RTSPClient(rtsp_url=rtsp_url)

    # capture frame
    default_folder = configuration.get_param("frame", "storage_path")
    client_rtsp.set_default_folder(default_folder=default_folder)

    if use_file:
        if file:
            print(file.filename)
            frame_to_process = client_rtsp.load_frame_from_file(file=file)
    else:
        frame_to_process = client_rtsp.get_frame(filename="0.frame_origine")

    # rotate frame
    rotate = configuration.get_param("vision", "rotate")
    print(f"rotate: {rotate}")
    if rotate > 0:
        print(f"rotate image to {rotate} degres")
        frame_to_process = client_rtsp.rotate_frame(angle=rotate, filename="1.rotate")

    # improve frame
    contrast_active = bool(
        configuration.get_param("rtsp", "image", "contrast", "active")
    )
    contrast_alpha = configuration.get_param("rtsp", "image", "contrast", "alpha")
    contrast_beta = configuration.get_param("rtsp", "image", "contrast", "beta")
    sharpen_active = bool(configuration.get_param("rtsp", "image", "sharpen", "active"))
    sharpen_amount = configuration.get_param("rtsp", "image", "sharpen", "amount")
    sharpen_threshold = configuration.get_param("rtsp", "image", "sharpen", "threshold")
    exposure_active = bool(
        configuration.get_param("rtsp", "image", "exposure", "active")
    )
    exposure_in_range = tuple(
        configuration.get_param("rtsp", "image", "exposure", "in_range")
    )
    exposure_out_range = tuple(
        configuration.get_param("rtsp", "image", "exposure", "out_range")
    )
    convert_to_grey = bool(configuration.get_param("rtsp", "image", "convert_to_grey"))
    convert_to_bgr = bool(configuration.get_param("rtsp", "image", "convert_to_bgr"))

    fill_image = bool(configuration.get_param("rtsp", "image", "fill_image", "active"))

    if convert_to_bgr:
        frame_to_process = client_rtsp.convert_rgb2bgr(
            filename="2.improve_convert_to_bgr"
        )
    if convert_to_grey:
        frame_to_process = client_rtsp.convert_bgr2gray(
            filename="3.improve_convert_to_grey"
        )
    if exposure_active:
        frame_to_process = client_rtsp.improve_exposure_intensity(
            in_range=exposure_in_range,
            out_range=exposure_out_range,
            filename="4.improve_exposure",
        )

    if contrast_active:
        frame_to_process = client_rtsp.adjust_contrast(
            alpha=contrast_alpha, beta=contrast_beta, filename="5.improve_contrast"
        )

    if sharpen_active:
        frame_to_process = client_rtsp.sharpen_image(
            amount=sharpen_amount,
            threshold=sharpen_threshold,
            filename="6.improve_sharpen",
        )
    # frame_to_process = client_rtsp.convert_bgr2gray()
    # frame_to_process = client_rtsp.adaptive_threshold()

    if fill_image:
        coordinates_selection = configuration.get_param(
            "rtsp", "image", "fill_image", "coordinates"
        )

        coordinates_selection = coordinates_selection.lower().strip()
        coordinates = configuration.get_param(
            "vision", "coordinates", coordinates_selection
        )
        print(f"{coordinates_selection} {coordinates}")

        if (
            coordinates.get("x") is not None
            and coordinates.get("y") is not None
            and coordinates.get("width") is not None
            and coordinates.get("height") is not None
        ):
            # Apply exact coordinates without offset padding
            frame_to_process = client_rtsp.crope_image(
                x=int(coordinates["x"]),
                y=int(coordinates["y"]),
                width=int(coordinates["width"]),
                height=int(coordinates["height"]),
                filename="6.improve_fill_image",
            )

    client_rtsp.write_output_file(name="7.frame_improve", frame=frame_to_process)
    return frame_to_process


def service_process(
    increase_cron_count: bool = False, use_file: bool = False, file=None
):

    frame_to_process = create_improved_frame(use_file=use_file, file=file)
    default_folder = configuration.get_param("frame", "storage_path")

    # Determine OCR Engine
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
            filename="8.esseract_optimized",
        )

        # Draw text boxes mimic
        client_azure = AzureClient(vision_key="mock", endpoint_url="mock")
        client_azure.default_folder = default_folder
        client_azure.draw_text_boxes(
            text_regions=text_regions,
            frame=frame_to_process,
            filename="9.azure_vision_draw_boxes",
        )
    else:
        # init Azure client
        logger.info("Using Azure OCR Engine")
        subscription_key = configuration.get_param("vision", "key")
        endpoint = configuration.get_param("vision", "endpoint")
        # vision_integer = configuration.get_param("vision", "coordinates", "integer")
        # vision_digit = configuration.get_param("vision", "coordinates", "digit")
        # vision_all = configuration.get_param("vision", "coordinates", "digit")

        client_azure = AzureClient(vision_key=subscription_key, endpoint_url=endpoint)
        client_azure.default_folder = default_folder

        # call azure vision api
        result = client_azure.process_image(
            frame=frame_to_process
        )  # implement logic for integer, digit or all

        logger.info(f"Azure OCR Result: {result}")

        text_regions = client_azure.get_regions(result=result)
        logger.info(f"Azure OCR Text Regions: {text_regions}")
        client_azure.draw_text_boxes(
            text_regions=text_regions,
            frame=frame_to_process,
            filename="10.azure_vision_draw_boxes",
        )

    vision_counter = int(configuration.get_param("vision", "counter"))
    configuration.set_param("vision", "counter", value=vision_counter + 1)
    text_regions = client_azure.get_regions(result=result)
    logger.info(f"Azure OCR Text Regions: {text_regions}")

    client_azure.draw_text_boxes(
        text_regions=text_regions,
        frame=frame_to_process,
        filename="11.azure_vision_draw_boxes",
    )

    # process the result of vision
    line_with_data = configuration.get_param("vision", "line_with_data") or 0
    print(line_with_data)

    if not result or len(result) == 0 or not result[0].lines:
        return ValueError("No lines of text were recognized by the OCR engine.")

    raw_result = result[0].lines[line_with_data].text
    print(raw_result)
    try:
        result_values = generate_result(raw_result=raw_result)
    except Exception as e:
        print(f"Error generating result from OCR text: {e}")
        return ValueError("couldn't get the digitalisation of the meter")

    # save result
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

    # publish value to MQTT
    client_mqtt = MqttCLient()
    client_mqtt.mqtt_publish_device()
    # data = json.loads(service_process())
    client_mqtt.send_value(values=result_values)

    # create return object
    data = {
        "images": {
            "image_source": f"{default_folder}/0.frame_origine.jpg",
            "image_improve": f"{default_folder}/7.frame_improve.jpg",
            "image_vision": f"{default_folder}/11.azure_vision_draw_boxes.jpg",
        },
        "result": result_values,
    }

    if increase_cron_count:
        curent_count = int(configuration.get_param("service", "counter"))
        print(f"curent_count: {curent_count}")
        print(f"new count: {curent_count + 1}")
        configuration.set_param("service", "counter", value=curent_count + 1)

    return data
