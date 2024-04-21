from flask import (
    Flask,
    render_template,
    Response,
    request,
    jsonify,
    make_response,
    redirect,
    url_for,
)
from utils.rtsp_client import RTSPClient
from utils.azure_client import AzureClient
from utils.utils import volume_converter, time_to_cron
from utils.configuration import YamlConfigLoader
import cv2
import os
import time
import logging
import base64

app = Flask(__name__)
rtsp_url = os.environ["RTSP_URL"]
subscription_key = os.environ["VISION_KEY"]
endpoint = os.environ["VISION_ENDPOINT"]

configuration = YamlConfigLoader()


@app.route("/")
def index():
    # statut_azure_vision = "Azure visition is not connected"
    # client_azure = AzureClient(vision_key=subscription_key, endpoint_url=endpoint)
    # print(client_azure.verify_credentials())
    # if client_azure.verify_credentials():
    #     statut_azure_vision = "Azure visition is connected"
    # print(statut_azure_vision)

    return render_template("index.html")


@app.route("/config")
def config():
    return render_template("config.html", config=configuration.data)


@app.route("/save_config", methods=["POST"])
def save_config():

    # Azure vision config
    vision_key = request.form["vision_key"]

    if (
        vision_key != configuration.get_param("vision", "key")
        and vision_key != "********************************"
    ):
        print("Vision key changed")
        configuration.set_param("vision", "key", value=vision_key)

    endpoint_url = request.form["endpoint_url"]
    configuration.set_param("vision", "endpoint", value=endpoint_url)

    # RTSP config
    rtsp_url = request.form["rtsp_url"]
    configuration.set_param("rtsp", "url", value=rtsp_url)

    # MQTT config
    mqtt_server = request.form["mqtt_server"]
    configuration.set_param("mqtt", "server", value=mqtt_server)
    mqtt_user = request.form["mqtt_user"]
    configuration.set_param("mqtt", "user", value=mqtt_user)
    mqtt_password = request.form["mqtt_password"]
    if (
        mqtt_password != configuration.get_param("mqtt", "password")
        and mqtt_password != "********************************"
    ):
        print("MQTT user password changed")
        configuration.set_param("mqtt", "password", value=mqtt_password)

    cron_time = request.form["cron_time"]
    configuration.set_param("service", "cron", value=cron_time)
    print(time_to_cron(cron_time))
    return redirect(url_for("config"))


@app.route("/video_feed")
def video_feed():
    client = RTSPClient(rtsp_url=rtsp_url, save_frame=False)
    return Response(
        client.get_stream(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@app.route("/run_process")
def run_process():

    # init rtsp client
    client_rtsp = RTSPClient(rtsp_url=rtsp_url, save_frame=True)

    # capture frame
    default_folder = configuration.get_param("frame", "storage_path")
    client_rtsp.set_default_folder(default_folder=default_folder)
    frame = client_rtsp.get_frame()

    # improve frame
    client_rtsp.convert_rgb2bgr()
    frame_to_process = client_rtsp.improve_exposure_intensity()
    # init Azure client
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

    data = jsonify(
        image_source="static/img/frame_origine.jpg",
        image_improve="static/img/improve.jpg",
        image_vision="static/img/vision.jpg",
        result=text,
    )
    return data


if __name__ == "__main__":
    app = Flask(__name__)
    app._static_folder = ""
    app.debug = True
    app.run()
