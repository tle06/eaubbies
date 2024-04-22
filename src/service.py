from utils.rtsp_client import RTSPClient
from utils.azure_client import AzureClient
from utils.configuration import YamlConfigLoader
from utils.utils import volume_converter
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

    raw_result = result[0].lines[0].text
    raw_result_without_space = raw_result.replace(" ", "")
    cubic_meters = int(raw_result_without_space[:6])
    centiliters = int(raw_result_without_space[7:])
    cubic_meters_to_liters = volume_converter(
        number=cubic_meters, from_unit="m3", to_unit="l"
    )
    centiliters_to_liters = volume_converter(
        number=cubic_meters, from_unit="cl", to_unit="l"
    )
    total_liters = cubic_meters_to_liters + centiliters_to_liters

    text = {
        "raw_result": raw_result,
        "raw_result_without_space": raw_result_without_space,
        "cubic_meters": cubic_meters,
        "centiliters": centiliters,
        "cubic_meters_to_liters": cubic_meters_to_liters,
        "centiliters_to_liters": centiliters_to_liters,
        "total_liters": total_liters,
    }

    data = json.dumps(
        {
            "image_source": f"{default_folder}/origine.jpg",
            "image_improve": f"{default_folder}/improve.jpg",
            "image_vision": f"{default_folder}/vision.jpg",
            "result": text,
        }
    )

    return data
