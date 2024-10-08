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
path_frame_folder = configuration.get_param("frame", "storage_path")
app.logger.info(f"Frame folder path: {path_frame_folder}")
os.makedirs(path_frame_folder, exist_ok=True)
command = "/root/.local/share/pypoetry/venv/bin/poetry run python /app/cron.py"
register_cron_task(
    command=command, selected_time=configuration.get_param("service", "cron")
)


@app.route("/")
@app.route("/index")
def index():
    conf = YamlConfigLoader()
    init_config = bool(conf.get_param("setup", "init_config"))

    app.logger.info(f"init_config value in index: {init_config}")

    if not init_config:
        app.logger.info("redirect to init")
        return redirect(url_for("init"))

    return render_template("index.html", config=configuration.data)


@app.route("/init")
def init():

    return render_template("init-config.html", config=configuration.data)


@app.route("/config")
def config():
    return render_template("config.html", config=configuration.data)


@app.route("/video")
def video():
    return render_template("video.html")


@app.route("/frames")
def frames():

    try:
        files = os.listdir(configuration.get_param("frame", "storage_path"))
    except Exception as e:
        app.logger.error(f"Error: {e}")
        files = ""
    return render_template("frames.html", files=files)


@app.route("/download/<path:filename>")
def download_file(filename):
    return send_from_directory(
        configuration.get_param("frame", "storage_path"), filename, as_attachment=True
    )


@app.route("/save_config", methods=["POST"])
def save_config():

    # Azure vision config
    if request.form.get("vision_key"):
        vision_key = request.form["vision_key"]

        if (
            vision_key != configuration.get_param("vision", "key")
            and vision_key != "********************************"
        ):
            app.logger.info("Vision key updated")
            configuration.set_param("vision", "key", value=vision_key)

    if request.form.get("endpoint_url"):
        endpoint_url = request.form["endpoint_url"]
        configuration.set_param("vision", "endpoint", value=endpoint_url)

    if request.form.get("vision_integer_digit"):
        vision_integer_digit = request.form["vision_integer_digit"]
        configuration.set_param(
            "vision", "integer", "digit", value=vision_integer_digit
        )

    if request.form.get("vision_integer_unit_of_measurement"):
        vision_integer_unit_of_measurement = request.form[
            "vision_integer_unit_of_measurement"
        ]
        configuration.set_param(
            "vision",
            "integer",
            "unit_of_measurement",
            value=vision_integer_unit_of_measurement,
        )

    if request.form.get("vision_decimal_digit"):
        vision_decimal_digit = request.form["vision_decimal_digit"]
        configuration.set_param(
            "vision", "decimal", "digit", value=vision_decimal_digit
        )
    if request.form.get("vision_decimal_unit_of_measurement"):
        vision_decimal_unit_of_measurement = request.form[
            "vision_decimal_unit_of_measurement"
        ]

        configuration.set_param(
            "vision",
            "decimal",
            "unit_of_measurement",
            value=vision_decimal_unit_of_measurement,
        )

    # RTSP config
    if request.form.get("rtsp_url"):
        rtsp_url = request.form["rtsp_url"]
        configuration.set_param("rtsp", "url", value=rtsp_url)

    # MQTT config
    if request.form.get("mqtt_server"):
        mqtt_server = request.form["mqtt_server"]
        configuration.set_param("mqtt", "server", value=mqtt_server)

    if request.form.get("mqtt_user"):
        mqtt_user = request.form["mqtt_user"]
        configuration.set_param("mqtt", "user", value=mqtt_user)

    if request.form.get("mqtt_password"):
        mqtt_password = request.form["mqtt_password"]
        if (
            mqtt_password != configuration.get_param("mqtt", "password")
            and mqtt_password != "********************************"
        ):
            app.logger.info("MQTT user password changed")
            configuration.set_param("mqtt", "password", value=mqtt_password)
    if request.form.get("mqtt_device_name"):
        mqtt_device_name = request.form["mqtt_device_name"]
        configuration.set_param("mqtt", "device", "name", value=mqtt_device_name)

    if request.form.get("mqtt_device_node_id"):
        mqtt_device_node_id = request.form["mqtt_device_node_id"]
        configuration.set_param("mqtt", "device", "node_id", value=mqtt_device_node_id)

    if request.form.get("mqtt_device_unique_id"):
        mqtt_device_unique_id = request.form["mqtt_device_unique_id"]
        configuration.set_param(
            "mqtt", "device", "unique_id", value=mqtt_device_unique_id
        )
    if request.form.get("mqtt_discovery_prefix"):
        mqtt_discovery_prefix = request.form["mqtt_discovery_prefix"]
        configuration.set_param("mqtt", "discovery_prefix", value=mqtt_discovery_prefix)
    if request.form.get("mqtt_sensors_water_unit_of_measurement"):
        mqtt_sensors_water_unit_of_measurement = request.form[
            "mqtt_sensors_water_unit_of_measurement"
        ].lower()
        configuration.set_param(
            "mqtt",
            "sensors",
            "water",
            "unit_of_measurement",
            value=mqtt_sensors_water_unit_of_measurement,
        )

    if request.form.get("con_time"):
        cron_time = request.form["cron_time"]
        configuration.set_param("service", "cron", value=cron_time)
        app.logger.info(f"cron time update: {time_to_cron(cron_time)}")
        register_cron_task(command=command, selected_time=cron_time)

    if request.referrer.endswith("/init"):
        return Response(status=200)

    return redirect(url_for("config"))


@app.route("/video_feed")
def video_feed():
    rtsp_url = configuration.get_param("rtsp", "url")
    client = RTSPClient(rtsp_url=rtsp_url, save_frame=False)
    return Response(
        client.get_stream(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@app.route("/run_process", methods=["GET", "POST"])
def run_process():
    use_file = False
    file = None

    if request.method == "POST":
        # Handle file upload via POST
        if "file" not in request.files:
            return jsonify({"error": "No file part"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "No selected file"}), 400

        # Process the file (e.g., save it, process its contents, etc.)
        # Here you would handle the uploaded file, for example:
        # file.save(os.path.join('/path/to/save', file.filename))

        app.logger.info("[RUN PROCESS] File mode will be used")
        app.logger.info(f"[RUN PROCESS] File received: {file.filename}")
        use_file = True

    # Call your service function
    try:
        result = service_process(use_file=use_file, file=file)
        if isinstance(result, ValueError):
            return jsonify({"error": str(result)})
        app.logger.info(result)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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

    try:
        response = client_mqtt.mqtt_publish_device()
        app.logger.info(f"MQTT response: {response}")

        result = json.dumps(
            {
                "mqtt": response,
            }
        )

        return result
    except Exception as e:
        app.logger.info("Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/send_edit", methods=["POST"])
def receive_coordinates():
    data = request.json
    # Process the received coordinates here
    app.logger.info("Received coordinates:", data)

    for d in data:
        configuration.set_param(
            "vision", "coordinates", d["name"], value=d["coordinates"]
        )
        configuration.set_param("vision", "rotate", value=d["rotate"])

    init_config = bool(configuration.get_param("setup", "init_config"))
    app.logger.info(f"init_config value in send_edit: {init_config}")
    if not init_config:
        configuration.set_param("setup", "init_config", value=True)

    return redirect(url_for("index"), code=302)


if __name__ == "__main__":
    app = Flask(__name__)
    app._static_folder = ""
    app.debug = True
    app.host = "0.0.0.0"
    app.run()
