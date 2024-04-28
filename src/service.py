from utils.rtsp_client import RTSPClient
from utils.azure_client import AzureClient
from utils.configuration import YamlConfigLoader
from utils.utils import volume_converter, generate_result
from utils.mqtt import MqttCLient
import json

configuration = YamlConfigLoader()


def service_process():

    # init rtsp client
    rtsp_url = configuration.get_param("rtsp", "url")
    client_rtsp = RTSPClient(rtsp_url=rtsp_url)

    # capture frame
    default_folder = configuration.get_param("frame", "storage_path")
    client_rtsp.set_default_folder(default_folder=default_folder)
    frame = client_rtsp.get_frame()

    # improve frame
    client_rtsp.convert_rgb2bgr()
    frame_to_process = client_rtsp.improve_exposure_intensity()
    client_rtsp.write_output_file(name="improve", frame=frame_to_process)
    # init Azure client

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
    raw_result = result[0].lines[line_with_data].text
    result_values = generate_result(raw_result=raw_result)

    # publish value to MQTT
    client_mqtt = MqttCLient()
    client_mqtt.mqtt_publish_device()
    client_mqtt.send_value(value=result_values.get("total_liters"), measurement="water")
    client_mqtt.send_value(
        value=result_values.get("raw_result_without_space"), measurement="raw"
    )

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
