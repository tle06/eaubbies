from flask import (
    Flask,
    render_template,
    Response,
    request,
    jsonify,
    redirect,
    url_for,
    send_from_directory,
)
from utils.rtsp_client import RTSPClient
from utils.utils import time_to_cron, register_cron_task, get_cron_status
from utils.configuration import YamlConfigLoader
from utils.mqtt import MqttCLient
from service import service_process
import os
import logging
import json

app = Flask(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("troubleshoot")
configuration = YamlConfigLoader()
path_frame_folder = configuration.get_param("frame", "storage_path")
logger.info(f"Frame folder path: {path_frame_folder}")
os.makedirs(path_frame_folder, exist_ok=True)
CRON_COMMAND = "/app/.venv/bin/python /app/cron.py"
register_cron_task(
    command=CRON_COMMAND, selected_time=configuration.get_param("service", "cron")
)


@app.route("/")
@app.route("/index")
def index():
    conf = YamlConfigLoader()
    if not bool(conf.get_param("setup", "init_config")):
        return redirect(url_for("init"))
    return render_template("index.html", config=configuration.data)


@app.route("/init")
def init():
    return render_template("init-config.html", config=configuration.data)


@app.route("/config")
def config():
    cron_status = get_cron_status(CRON_COMMAND)
    return render_template("config.html", config=configuration.data, cron_status=cron_status)


@app.route("/video")
def video():
    return render_template("video.html")


@app.route("/frames")
def frames():
    try:
        files = os.listdir(configuration.get_param("frame", "storage_path"))
    except Exception as e:
        logger.error(f"Error: {e}")
        files = []
    return render_template("frames.html", files=files)


@app.route("/download/<path:filename>")
def download_file(filename):
    return send_from_directory(
        configuration.get_param("frame", "storage_path"), filename, as_attachment=True
    )


@app.route("/save_config", methods=["POST"])
def save_config():

    # ── OCR engine ──
    if request.form.get("vision_engine"):
        configuration.set_param("vision", "engine", value=request.form["vision_engine"])
    if request.form.get("tesseract_config"):
        configuration.set_param("vision", "tesseract_config", value=request.form["tesseract_config"])
    if request.form.get("vision_key"):
        key = request.form["vision_key"]
        if key != "********************************" and key != configuration.get_param("vision", "key"):
            configuration.set_param("vision", "key", value=key)
    if request.form.get("endpoint_url"):
        configuration.set_param("vision", "endpoint", value=request.form["endpoint_url"])
    if request.form.get("vision_integer_digit"):
        configuration.set_param("vision", "integer", "digit", value=int(request.form["vision_integer_digit"]))
    if request.form.get("vision_integer_unit_of_measurement"):
        configuration.set_param("vision", "integer", "unit_of_measurement", value=request.form["vision_integer_unit_of_measurement"])
    if request.form.get("vision_decimal_digit"):
        configuration.set_param("vision", "decimal", "digit", value=int(request.form["vision_decimal_digit"]))
    if request.form.get("vision_decimal_unit_of_measurement"):
        configuration.set_param("vision", "decimal", "unit_of_measurement", value=request.form["vision_decimal_unit_of_measurement"])

    # ── Image optimisation ──
    configuration.set_param("rtsp", "image", "convert_to_bgr",  value="img_convert_bgr"  in request.form)
    configuration.set_param("rtsp", "image", "convert_to_grey", value="img_convert_grey" in request.form)
    configuration.set_param("rtsp", "image", "exposure", "active",   value="img_exposure_active" in request.form)
    configuration.set_param("rtsp", "image", "contrast", "active",   value="img_contrast_active" in request.form)
    configuration.set_param("rtsp", "image", "sharpen",  "active",   value="img_sharpen_active"  in request.form)
    configuration.set_param("rtsp", "image", "crop_image", "active", value="img_crop_active"     in request.form)

    if request.form.get("img_exposure_in_min") and request.form.get("img_exposure_in_max"):
        configuration.set_param("rtsp", "image", "exposure", "in_range",
            value=[int(request.form["img_exposure_in_min"]), int(request.form["img_exposure_in_max"])])
    if request.form.get("img_exposure_out_min") and request.form.get("img_exposure_out_max"):
        configuration.set_param("rtsp", "image", "exposure", "out_range",
            value=[int(request.form["img_exposure_out_min"]), int(request.form["img_exposure_out_max"])])
    if request.form.get("img_contrast_alpha"):
        configuration.set_param("rtsp", "image", "contrast", "alpha", value=float(request.form["img_contrast_alpha"]))
    if request.form.get("img_contrast_beta"):
        configuration.set_param("rtsp", "image", "contrast", "beta",  value=int(request.form["img_contrast_beta"]))
    if request.form.get("img_sharpen_amount"):
        configuration.set_param("rtsp", "image", "sharpen", "amount",    value=float(request.form["img_sharpen_amount"]))
    if request.form.get("img_sharpen_threshold"):
        configuration.set_param("rtsp", "image", "sharpen", "threshold", value=int(request.form["img_sharpen_threshold"]))
    if request.form.get("img_crop_coordinates"):
        configuration.set_param("rtsp", "image", "crop_image", "coordinates", value=request.form["img_crop_coordinates"])

    # ── RTSP ──
    if request.form.get("rtsp_url"):
        configuration.set_param("rtsp", "url", value=request.form["rtsp_url"])

    # ── MQTT ──
    if request.form.get("mqtt_server"):
        configuration.set_param("mqtt", "server", value=request.form["mqtt_server"])
    if request.form.get("mqtt_port"):
        configuration.set_param("mqtt", "port", value=int(request.form["mqtt_port"]))
    if request.form.get("mqtt_user"):
        configuration.set_param("mqtt", "user", value=request.form["mqtt_user"])
    if request.form.get("mqtt_password"):
        pwd = request.form["mqtt_password"]
        if pwd != "********************************" and pwd != configuration.get_param("mqtt", "password"):
            configuration.set_param("mqtt", "password", value=pwd)
    if request.form.get("mqtt_device_name"):
        configuration.set_param("mqtt", "device", "name", value=request.form["mqtt_device_name"])
    if request.form.get("mqtt_device_node_id"):
        configuration.set_param("mqtt", "device", "node_id", value=request.form["mqtt_device_node_id"])
    if request.form.get("mqtt_device_unique_id"):
        configuration.set_param("mqtt", "device", "unique_id", value=request.form["mqtt_device_unique_id"])
    if request.form.get("mqtt_discovery_prefix"):
        configuration.set_param("mqtt", "discovery_prefix", value=request.form["mqtt_discovery_prefix"])
    if request.form.get("mqtt_sensors_water_unit_of_measurement"):
        configuration.set_param("mqtt", "sensors", "water", "unit_of_measurement",
            value=request.form["mqtt_sensors_water_unit_of_measurement"].lower())

    # ── Cron ──
    if request.form.get("cron_time"):
        cron_time = request.form["cron_time"]
        configuration.set_param("service", "cron", value=cron_time)
        register_cron_task(command=CRON_COMMAND, selected_time=cron_time)

    if request.referrer and request.referrer.endswith("/init"):
        return Response(status=200)
    return redirect(url_for("config"))


@app.route("/cron_status")
def cron_status():
    """Return the live cron job status as JSON."""
    status = get_cron_status(CRON_COMMAND)
    return jsonify(status)


@app.route("/register_cron", methods=["POST"])
def register_cron():
    """Manually (re-)register the cron job at the configured time."""
    try:
        selected_time = configuration.get_param("service", "cron")
        register_cron_task(command=CRON_COMMAND, selected_time=selected_time)
        status = get_cron_status(CRON_COMMAND)
        return jsonify({"success": True, "cron_status": status})
    except Exception as e:
        logger.error(f"register_cron error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


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
        if "file" not in request.files:
            return jsonify({"error": "No file part"}), 400
        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "No selected file"}), 400
        logger.info(f"[RUN PROCESS] File received: {file.filename}")
        use_file = True

    try:
        result = service_process(use_file=use_file, file=file)
        if isinstance(result, ValueError):
            return jsonify({"error": str(result)})
        return jsonify(result)
    except Exception as e:
        logger.error(f"run_process error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/load_frame")
def load_frame():
    rtsp_url = configuration.get_param("rtsp", "url")
    client_rtsp = RTSPClient(rtsp_url=rtsp_url)
    default_folder = configuration.get_param("frame", "storage_path")
    client_rtsp.set_default_folder(default_folder=default_folder)
    client_rtsp.get_frame(filename="0.frame_origine")
    image_path = f"{default_folder}/0.frame_origine.jpg"
    return json.dumps(image_path)


@app.route("/create_sensor")
def create_sensor():
    client_mqtt = MqttCLient()
    try:
        response = client_mqtt.mqtt_publish_device()
        return json.dumps({"mqtt": response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/send_edit", methods=["POST"])
def receive_coordinates():
    data = request.json
    logger.info(f"Received coordinates: {data}")
    for d in data:
        coords = d["coordinates"]
        coords["active"] = bool(coords.get("width") and coords.get("height"))
        configuration.set_param("vision", "coordinates", d["name"], value=coords)
        configuration.set_param("vision", "rotate", value=float(d["rotate"]))
    if not bool(configuration.get_param("setup", "init_config")):
        configuration.set_param("setup", "init_config", value=True)
    return redirect(url_for("index"), code=302)


if __name__ == "__main__":
    app.debug = True
    app.run(host="0.0.0.0")
