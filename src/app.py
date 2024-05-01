from flask import (
    Flask,
    render_template,
    Response,
    request,
    jsonify,
    make_response,
    redirect,
    url_for,
    send_file,
    send_from_directory,
)
from utils.rtsp_client import RTSPClient
from utils.azure_client import AzureClient
from utils.utils import volume_converter, time_to_cron, register_cron_task
from utils.configuration import YamlConfigLoader
from utils.mqtt import MqttCLient
from service import service_process, create_improved_frame
from PIL import Image
import cv2
import os
import time
import logging
import base64
import json
import io

app = Flask(__name__)
configuration = YamlConfigLoader()
frames_directory = "static/img/frames"


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


@app.route("/frames")
def frames():

    files = os.listdir(frames_directory)
    return render_template("files.html", files=files)


@app.route("/download/<path:filename>")
def download_file(filename):
    return send_from_directory(frames_directory, filename, as_attachment=True)


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
    command = "echo hello_world"
    register_cron_task(command=command, selected_time=cron_time)
    return redirect(url_for("config"))


@app.route("/video_feed")
def video_feed():
    rtsp_url = configuration.get_param("rtsp", "url")
    client = RTSPClient(rtsp_url=rtsp_url, save_frame=False)
    return Response(
        client.get_stream(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@app.route("/run_process")
def run_process():
    result = service_process()
    return json.dumps(result)


@app.route("/load_frame")
def load_frame():
    rtsp_url = configuration.get_param("rtsp", "url")
    client_rtsp = RTSPClient(rtsp_url=rtsp_url)

    # capture frame
    default_folder = configuration.get_param("frame", "storage_path")
    client_rtsp.set_default_folder(default_folder=default_folder)
    client_rtsp.get_frame()

    default_folder = configuration.get_param("frame", "storage_path")
    image_path = f"{default_folder}/origine.jpg"
    # with open(image_path, "rb") as f:
    #     image_bytes = io.BytesIO(f.read())
    return json.dumps(image_path)


@app.route("/create_sensor")
def create_sensor():
    client_mqtt = MqttCLient()

    response = client_mqtt.mqtt_publish_device()
    print(response)

    result = json.dumps(
        {
            "mqtt": response,
        }
    )

    return result


@app.route("/send_coordinates", methods=["POST"])
def receive_coordinates():
    data = request.json
    # Process the received coordinates here
    print("Received coordinates:", data)

    for d in data:
        configuration.set_param(
            "vision", "coordinates", d["name"], value=d["coordinates"]
        )
    # Optionally, you can return a response to acknowledge the successful receipt of coordinates
    return jsonify({"message": "Coordinates received successfully"})


if __name__ == "__main__":
    app = Flask(__name__)
    app._static_folder = ""
    app.debug = True
    app.run()
