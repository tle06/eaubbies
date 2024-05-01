# from utils.rtsp_client import RTSPClient
# from utils.configuration import YamlConfigLoader
# from utils.azure_client import AzureClient

# config = YamlConfigLoader()
# rtsp_url = config.get_param("rtsp", "url")
# client_rtsp = RTSPClient(rtsp_url=rtsp_url)
# default_folder = config.get_param("frame", "storage_path")
# client_rtsp.set_default_folder(default_folder=default_folder)
# client_rtsp.load_frame_from_file(file="static/img/frames/origine.jpg")

# coordinates = config.get_param("vision", "coordinates")
# print(coordinates)
# x1 = int(coordinates["c_1"]["x"])
# y1 = int(coordinates["c_1"]["y"])
# h1 = int(coordinates["c_1"]["height"])
# w1 = int(coordinates["c_1"]["width"])

# x2 = int(coordinates["c_2"]["x"])
# y2 = int(coordinates["c_2"]["y"])
# h2 = int(coordinates["c_2"]["height"])
# w2 = int(coordinates["c_2"]["width"])
# frame_to_process = client_rtsp.crop_image(
#     x=x1, y=y1, width=w1, height=h1, filename="frame_cropped_1"
# )
# # crop2 = client_rtsp.crop_image(
# #     x=x2, y=y2, width=w2, height=h2, filename="frame_cropped_2"
# # )

# # frame_to_process = client_rtsp.join_images_with_dot(image1=crop1, image2=crop2)

# subscription_key = config.get_param("vision", "key")
# endpoint = config.get_param("vision", "endpoint")
# client_azure = AzureClient(vision_key=subscription_key, endpoint_url=endpoint)
# client_azure.default_folder = default_folder

# # call azure vision api
# result = client_azure.process_image(frame=frame_to_process)
# text_regions = client_azure.get_regions(result=result)
# image_vision = client_azure.draw_text_boxes(
#     text_regions=text_regions, frame=frame_to_process, output_image_name="vision"
# )

# # process the result of vision
# line_with_data = config.get_param("vision", "line_with_data") or 0
# print(line_with_data)

# for r in result:
#     for l in r.lines:
#         print(l.text)
# raw_result = result[0].lines[line_with_data].text
# print(raw_result)

from service import service_process, create_improved_frame

data = service_process()
