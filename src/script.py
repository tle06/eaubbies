from utils.azure_client import AzureClient
from utils.rtsp_client import RTSPClient
from utils.utils import volume_converter
import os
import cv2
from utils.configuration import YamlConfigLoader
import time
import logging

configuration = YamlConfigLoader()
default_folder = configuration.get_param("frame", "storage_path")

subscription_key = os.environ["VISION_KEY"]
endpoint = os.environ["VISION_ENDPOINT"]
rtsp_url = os.environ["RTSP_URL"]


client_rtsp = RTSPClient(rtsp_url=rtsp_url, save_frame=True)
client_rtsp.set_default_fodler(default_folder=default_folder)
client_rtsp.get_frame()
improve_frame = client_rtsp.convert_rgb2bgr()
improve_frame = client_rtsp.improve_exposure_intensity()


client_azure = AzureClient(endpoint_url=endpoint, vision_key=subscription_key)
client_azure.default_folder = default_folder
result = client_azure.process_image(frame=improve_frame)

text_regions = client_azure.get_regions(result=result)

configuration.set_param("vision", "curent_region", value=text_regions)
configuration.set_param("vision", "previous_region", value=text_regions)

raw = result[0].lines[0].text
print(raw)
counter = (result[0].lines[0].text).replace(" ", "")
cubic_meters = int(counter[:6])
centiliters = int(counter[7:])

print(counter)
print(cubic_meters)
print(centiliters)

cubic_meters_to_liters = volume_converter(
    number=cubic_meters, from_unit="m3", to_unit="l"
)
centiliters_to_liters = volume_converter(
    number=cubic_meters, from_unit="cl", to_unit="l"
)
total_liters = cubic_meters_to_liters + centiliters_to_liters

print("Total volume in liters:", total_liters)

draw_box = client_azure.draw_text_boxes(frame=improve_frame, text_regions=text_regions)

previous_value = configuration.get_param("result", "previous")
if previous_value:
    if total_liters > previous_value:
        print(f"total liter ({total_liters}) is > previous value ({previous_value})")
        configuration.set_param("result", "previous", value=total_liters)
        configuration.set_param("result", "current", value=total_liters)
else:
    print("no previous value")
    configuration.set_param("result", "previous", value=total_liters)
    configuration.set_param("result", "current", value=total_liters)
