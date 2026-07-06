from flask import (
    Flask,
    render_template,
    Response,
    request,
    jsonify,
    redirect,
    url_for,
    send_from_directory,
    send_file,
)
from utils.rtsp_client import RTSPClient
from utils.utils import time_to_cron, register_cron_task, get_cron_status
from utils.configuration import YamlConfigLoader
from utils.mqtt import MqttCLient
from service import service_process
import os
import io
import zipfile
import logging
import json
from datetime import datetime, timedelta

LOG_FILE = "/tmp/eaubbies.log"

app = Flask(__name__)

# ── Logging setup ─────────────────────────────────────────────────────────────
log_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.INFO)

# File handler — persists logs for the viewer page
file_handler = logging.FileHandler(LOG_FILE)
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.DEBUG)

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(console_handler)
root_logger.addHandler(file_handler)

logger = logging.getLogger("troubleshoot")
# ─────────────────────────────────────────────────────────────────────────────

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
    # Pass the YAML config so the template can read config['rtsp']['url']
    return render_template("video.html", config=configuration.data)


@app.route("/frames")
def frames():
    folder = configuration.get_param("frame", "storage_path")
    try:
        files = sorted(os.listdir(folder))
    except Exception as e:
        logger.error(f"Error listing frames: {e}")
        files = []
    return render_template("frames.html", files=files)


@app.route("/download/<path:filename>")
def download_file(filename):
    return send_from_directory(
        configuration.get_param("frame", "storage_path"), filename, as_attachment=True
    )


@app.route("/delete_frame/<path:filename>", methods=["DELETE"])
def delete_frame(filename):
    folder = configuration.get_param("frame", "storage_path")
    filepath = os.path.join(folder, filename)
    try:
        if not os.path.abspath(filepath).startswith(os.path.abspath(folder)):
            return jsonify({"error": "Invalid path"}), 400
        os.remove(filepath)
        return jsonify({"success": True})
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), 404
    except Exception as e:
        logger.error(f"delete_frame error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/delete_all_frames", methods=["POST"])
def delete_all_frames():
    folder = configuration.get_param("frame", "storage_path")
    deleted, errors = [], []
    try:
        for f in os.listdir(folder):
            fp = os.path.join(folder, f)
            if os.path.isfile(fp):
                try:
                    os.remove(fp)
                    deleted.append(f)
                except Exception as e:
                    errors.append({"file": f, "error": str(e)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"deleted": deleted, "errors": errors})


@app.route("/download_all_frames")
def download_all_frames():
    folder = configuration.get_param("frame", "storage_path")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(os.listdir(folder)):
            fp = os.path.join(folder, f)
            if os.path.isfile(fp):
                zf.write(fp, f)
    buf.seek(0)
    return send_file(
        buf,
        mimetype="application/zip",
        as_attachment=True,
        download_name="frames.zip",
    )


@app.route("/logs")
def logs():
    """Display the last 30 days of log entries, most recent first."""
    cutoff = datetime.now() - timedelta(days=30)
    entries = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as fh:
            for line in fh:
                line = line.rstrip("\n")
                if not line:
                    continue
                # Determine log level for colour-coding
                level = "INFO"
                if " - ERROR - " in line:
                    level = "ERROR"
                elif " - WARNING - " in line:
                    level = "WARNING"
                elif " - DEBUG - " in line:
                    level = "DEBUG"
                # Filter entries older than 30 days
                try:
                    ts_str = line.split(" - ")[0].strip()
                    ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S,%f")
                    if ts < cutoff:
                        continue
                except Exception:
                    pass
                entries.append({"line": line, "level": level})
    # Most recent first
    entries.reverse()
    logger.info(f"Logs page accessed — {len(entries)} entries shown")
    return render_template("logs.html", entries=entries)


@app.route("/logs/download")
def logs_download():
    """Download the raw log file."""
    if not os.path.exists(LOG_FILE):
        return jsonify({"error": "Log file not found"}), 404
    logger.info("Log file downloaded by user")
    return send_file(
        LOG_FILE,
        mimetype="text/plain",
        as_attachment=True,
        download_name="eaubbies.log",
    )


@app.route("/save_config", methods=["POST"])
def save_config():

    # ── OCR engine ──
    if request.form.get("vision_engine"):
        configuration.set_param("vision", "engine", value=request.form["vision_engine"])
        logger.info(f"Vision engine updated to: {request.form['vision_engine']}")
    if request.form.get("tesseract_config"):
        configuration.set_param("vision", "tesseract_config", value=request.form["tesseract_config"])
        logger.info(f"Tesseract config updated: {request.form['tesseract_config']}")
    if request.form.get("vision_key"):
        key = request.form["vision_key"]
        if key != "********************************" and key != configuration.get_param("vision", "key"):
            configuration.set_param("vision", "key", value=key)
            logger.info("Vision API key updated")
    if request.form.get("endpoint_url"):
        configuration.set_param("vision", "endpoint", value=request.form["endpoint_url"])
        logger.info(f"Vision endpoint updated: {request.form['endpoint_url']}")
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
        logger.info(f"RTSP URL updated: {request.form['rtsp_url']}")

    # ── MQTT ──
    if request.form.get("mqtt_server"):
        configuration.set_param("mqtt", "server", value=request.form["mqtt_server"])
        logger.info(f"MQTT server updated: {request.form['mqtt_server']}")
    if request.form.get("mqtt_port"):
        configuration.set_param("mqtt", "port", value=int(request.form["mqtt_port"]))
    if request.form.get("mqtt_user"):
        configuration.set_param("mqtt", "user", value=request.form["mqtt_user"])
    if request.form.get("mqtt_password"):
        pwd = request.form["mqtt_password"]
        if pwd != "********************************" and pwd != configuration.get_param("mqtt", "password"):
            configuration.set_param("mqtt", "password", value=pwd)
            logger.info("MQTT password updated")
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
        logger.info(f"Cron schedule updated: {cron_time}")

    logger.info("Configuration saved successfully")

    if request.referrer and request.referrer.endswith("/init"):
        return Response(status=200)
    return redirect(url_for("config"))


@app.route("/cron_status")
def cron_status():
    status = get_cron_status(CRON_COMMAND)
    return jsonify(status)


@app.route("/register_cron", methods=["POST"])
def register_cron():
    try:
        selected_time = configuration.get_param("service", "cron")
        register_cron_task(command=CRON_COMMAND, selected_time=selected_time)
        status = get_cron_status(CRON_COMMAND)
        logger.info(f"Cron task registered, status: {status}")
        return jsonify({"success": True, "cron_status": status})
    except Exception as e:
        logger.error(f"register_cron error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/video_feed")
def video_feed():
    rtsp_url = configuration.get_param("rtsp", "url")
    logger.info(f"Starting video feed from: {rtsp_url}")
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
    logger.info(f"[RUN PROCESS] Starting service process (use_file={use_file})")
    try:
        result = service_process(use_file=use_file, file=file)
        if isinstance(result, ValueError):
            logger.warning(f"[RUN PROCESS] Service returned error: {result}")
            return jsonify({"error": str(result)})
        logger.info("[RUN PROCESS] Service process completed successfully")
        return jsonify(result)
    except Exception as e:
        logger.error(f"run_process error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/load_frame")
def load_frame():
    rtsp_url = configuration.get_param("rtsp", "url")
    logger.info(f"Loading frame from RTSP: {rtsp_url}")
    client_rtsp = RTSPClient(rtsp_url=rtsp_url)
    default_folder = configuration.get_param("frame", "storage_path")
    client_rtsp.set_default_folder(default_folder=default_folder)
    client_rtsp.get_frame(filename="0.frame_origine")
    image_path = f"{default_folder}/0.frame_origine.jpg"
    logger.info(f"Frame loaded and saved at: {image_path}")
    return json.dumps(image_path)


@app.route("/create_sensor")
def create_sensor():
    logger.info("Creating MQTT sensor...")
    client_mqtt = MqttCLient()
    try:
        response = client_mqtt.mqtt_publish_device()
        logger.info(f"MQTT sensor created: {response}")
        return json.dumps({"mqtt": response})
    except Exception as e:
        logger.error(f"create_sensor error: {e}", exc_info=True)
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
        logger.info(f"Coordinate saved — name={d['name']}, rotate={d['rotate']}, active={coords['active']}")
    if not bool(configuration.get_param("setup", "init_config")):
        configuration.set_param("setup", "init_config", value=True)
        logger.info("Initial configuration marked as done")
    return redirect(url_for("index"), code=302)


if __name__ == "__main__":
    app.debug = True
    app.run(host="0.0.0.0")
