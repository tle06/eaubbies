from utils.rtsp_client import RTSPClient
from utils.azure_client import AzureClient
from utils.configuration import YamlConfigLoader
from utils.utils import volume_converter, generate_result
from utils.mqtt import MqttCLient
import json

configuration = YamlConfigLoader()


def create_improved_frame():
    # init rtsp client
    rtsp_url = configuration.get_param("rtsp", "url")
    client_rtsp = RTSPClient(rtsp_url=rtsp_url)

    # capture frame
    default_folder = configuration.get_param("frame", "storage_path")
    client_rtsp.set_default_folder(default_folder=default_folder)
    frame_to_process = client_rtsp.get_frame()

    # improve frame
    contrast_active = configuration.get_param("rtsp", "image", "contrast", "active")
    contrast_alpha = configuration.get_param("rtsp", "image", "contrast", "alpha")
    contrast_beta = configuration.get_param("rtsp", "image", "contrast", "beta")
    sharpen_active = configuration.get_param("rtsp", "image", "sharpen", "active")
    sharpen_amount = configuration.get_param("rtsp", "image", "sharpen", "amount")
    sharpen_threshold = configuration.get_param("rtsp", "image", "sharpen", "threshold")
    exposure_active = configuration.get_param("rtsp", "image", "exposure", "active")
    exposure_in_range = tuple(
        configuration.get_param("rtsp", "image", "exposure", "in_range")
    )
    exposure_out_range = tuple(
        configuration.get_param("rtsp", "image", "exposure", "out_range")
    )
    convert_to_grey = configuration.get_param("rtsp", "image", "convert_to_grey")
    convert_to_bgr = configuration.get_param("rtsp", "image", "convert_to_bgr")

    if convert_to_bgr:
        frame_to_process = client_rtsp.convert_rgb2bgr()
    if convert_to_grey:
        frame_to_process = client_rtsp.convert_bgr2gray()
    if exposure_active:
        frame_to_process = client_rtsp.improve_exposure_intensity(
            in_range=exposure_in_range, out_range=exposure_out_range
        )

    if contrast_active:
        frame_to_process = client_rtsp.adjust_contrast(
            alpha=contrast_alpha, beta=contrast_beta
        )
    if sharpen_active:
        frame_to_process = client_rtsp.sharpen_image(
            amount=sharpen_amount, threshold=sharpen_threshold
        )

    client_rtsp.write_output_file(name="improve", frame=frame_to_process)
    return frame_to_process


def service_process():

    frame_to_process = create_improved_frame()
    # init Azure client
    default_folder = configuration.get_param("frame", "storage_path")
    subscription_key = configuration.get_param("vision", "key")
    endpoint = configuration.get_param("vision", "endpoint")
    client_azure = AzureClient(vision_key=subscription_key, endpoint_url=endpoint)
    client_azure.default_folder = default_folder

    # call azure vision api
    result = client_azure.process_image(frame=frame_to_process)
    text_regions = client_azure.get_regions(result=result)
    image_vision = client_azure.draw_text_boxes(
        text_regions=text_regions, frame=frame_to_process, output_image_name="vision"
    )

    # process the result of vision
    line_with_data = configuration.get_param("vision", "line_with_data") or 0
    print(line_with_data)
    raw_result = result[0].lines[line_with_data].text
    print(raw_result)

    try:
        result_values = generate_result(raw_result=raw_result)
    except Exception as e:
        print(e)
        raise ValueError("couldn't get the digitalisation of the meter")

    # save result
    current_value = float(result_values.get("total_liters"))
    previous_value = configuration.get_param("result", "previous")
    if not previous_value:
        configuration.set_param("result", "previous", value=current_value)
        previous_value = current_value

    if previous_value > current_value:
        raise ValueError(
            "previous value {previous_value} is > to current value {current_value}"
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
            "image_source": f"{default_folder}/origine.jpg",
            "image_improve": f"{default_folder}/improve.jpg",
            "image_vision": f"{default_folder}/vision.jpg",
        },
        "result": result_values,
    }

    return data
