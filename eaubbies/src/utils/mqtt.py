import json
import logging
import os

from paho.mqtt.client import CallbackAPIVersion, Client

from utils.configuration import YamlConfigLoader
from utils.utils import generate_unique_id

logger = logging.getLogger(__name__)


# All frames that can be produced by the pipeline.
# Each entry: (slug used in topic, human-readable label)
FRAME_SLOTS = [
    ("source", "Source frame"),
    ("rotate", "Rotated"),
    ("convert_bgr", "BGR convert"),
    ("convert_grey", "Greyscale"),
    ("exposure", "Exposure"),
    ("contrast", "Contrast"),
    ("sharpen", "Sharpen"),
    ("crop", "Crop"),
    ("final", "Final optimised"),
    ("ocr_boxes", "OCR bounding boxes"),
]


class MqttCLient:
    def __init__(self):
        self.config_loader = YamlConfigLoader()
        self.configuration = self.config_loader.data.get("mqtt", {})

        self.device_config = self.configuration.get("device", {})
        self.sensors_config = self.configuration.get("sensors", {})

        self.discovery_prefix = self.configuration.get(
            "discovery_prefix", "homeassistant"
        )
        self.name = self.device_config.get("name", "watermeter")

        self.sensor_water_uom = self.sensors_config.get("water", {}).get(
            "unit_of_measurement", "L"
        )

        self.device_unique_id = self.get_device_unique_id()
        self.topic = f"{self.discovery_prefix}/sensor/{self.name}"
        self.topic_config = f"{self.topic}/watermeter/config"
        self.topic_state = f"{self.topic}/watermeter/state"
        # Dedicated camera topic prefix — all frame entities live under
        # homeassistant/camera/{name}_frames/{slug}/
        self.topic_camera_base = f"{self.discovery_prefix}/camera/{self.name}_frames"

        self.mqtt_connection()

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _camera_image_topic(self, slug: str) -> str:
        return f"{self.topic_camera_base}/{slug}/image"

    def _camera_config_topic(self, slug: str) -> str:
        return f"{self.topic_camera_base}/{slug}/config"

    def mqtt_connection(self):
        mqtt_user = self.configuration.get("user")
        mqtt_password = self.configuration.get("password")
        mqtt_server = self.configuration.get("server")
        mqtt_port = int(self.configuration.get("port", 1883))

        self.client = Client(CallbackAPIVersion.VERSION2)
        self.client.enable_logger(logger)

        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message

        if mqtt_user and mqtt_password:
            self.client.username_pw_set(username=mqtt_user, password=mqtt_password)

        try:
            self.client.connect(host=mqtt_server, port=mqtt_port)
            self.client.loop_start()
        except Exception as e:
            logger.error(f"MQTT Connection failed: {e}")

    def get_device_unique_id(self):
        unique_id = self.device_config.get("unique_id")
        if not unique_id:
            logger.info("Generating unique ID")
            unique_id = generate_unique_id()
            self.config_loader.set_param("mqtt", "device", "unique_id", value=unique_id)
            logger.info(f"New ID generated: {unique_id}")
        return unique_id

    def on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            logger.info(f"Connected OK Returned code={rc}")
        else:
            logger.error(f"Bad connection Returned code={rc}")

    def on_disconnect(self, client, userdata, flags, rc, properties=None):
        if rc != 0:
            logger.warning(f"Unexpected disconnection. Code: {rc}")
        self.client.loop_stop()

    def on_message(self, client, userdata, message):
        msg_str = message.payload.decode("utf-8")
        logger.info(f"Message received: {msg_str} | Topic: {message.topic}")

    def publish_payload(self, topic: str, payload, qos: int = 0, retain: bool = True):
        logger.debug(f"Publishing to {topic}")
        response = self.client.publish(
            topic=topic, payload=payload, qos=qos, retain=retain
        )
        logger.info(f"Response is_published: {response.is_published()}")
        return response

    # ------------------------------------------------------------------
    # device / sensor discovery
    # ------------------------------------------------------------------

    def mqtt_publish_device(self):
        sensors = [
            {
                "name": "main",
                "payload": {
                    "name": self.name,
                    "device_class": None,
                    "unique_id": f"name_{self.device_unique_id}",
                    "state_topic": self.topic_state,
                    "value_template": self.name,
                    "device": {
                        "identifiers": self.device_unique_id,
                        "name": self.name,
                        "manufacturer": "eaubbies project",
                        "model": "V1",
                    },
                },
            },
            {
                "name": "water",
                "payload": {
                    "name": "watermeter",
                    "device_class": "water",
                    "unique_id": f"water_{self.device_unique_id}",
                    "state_topic": self.topic_state,
                    "device": {"identifiers": self.device_unique_id},
                    "unit_of_measurement": self.sensor_water_uom.upper(),
                    "value_template": "{{value_json.total_liters}}",
                },
            },
            {
                "name": "raw_result_without_space",
                "payload": {
                    "name": "raw result without space",
                    "device_class": None,
                    "unique_id": f"raw_result_without_space_{self.device_unique_id}",
                    "state_topic": self.topic_state,
                    "device": {"identifiers": self.device_unique_id},
                    "value_template": "{{value_json.raw_result_without_space}}",
                },
            },
            {
                "name": "left_number",
                "payload": {
                    "name": "left number",
                    "device_class": None,
                    "unique_id": f"left_number_{self.device_unique_id}",
                    "state_topic": self.topic_state,
                    "device": {"identifiers": self.device_unique_id},
                    "value_template": "{{value_json.left_number}}",
                },
            },
            {
                "name": "integer_digit",
                "payload": {
                    "name": "integer digit",
                    "device_class": None,
                    "unique_id": f"integer_digit_{self.device_unique_id}",
                    "state_topic": self.topic_state,
                    "device": {"identifiers": self.device_unique_id},
                    "value_template": "{{value_json.integer_digit}}",
                },
            },
            {
                "name": "integer_uom",
                "payload": {
                    "name": "integer uom",
                    "device_class": None,
                    "unique_id": f"integer_uom_{self.device_unique_id}",
                    "state_topic": self.topic_state,
                    "device": {"identifiers": self.device_unique_id},
                    "value_template": "{{value_json.integer_uom}}",
                },
            },
            {
                "name": "left_number_to_liters",
                "payload": {
                    "name": "left number to liters",
                    "device_class": None,
                    "unique_id": f"left_number_to_liters{self.device_unique_id}",
                    "state_topic": self.topic_state,
                    "device": {"identifiers": self.device_unique_id},
                    "value_template": "{{value_json.left_number_to_liters}}",
                },
            },
            {
                "name": "right_number",
                "payload": {
                    "name": "right number",
                    "device_class": None,
                    "unique_id": f"right_number{self.device_unique_id}",
                    "state_topic": self.topic_state,
                    "device": {"identifiers": self.device_unique_id},
                    "value_template": "{{value_json.right_number}}",
                },
            },
            {
                "name": "decimal_digit",
                "payload": {
                    "name": "decimal digit",
                    "device_class": None,
                    "unique_id": f"decimal_digit{self.device_unique_id}",
                    "state_topic": self.topic_state,
                    "device": {"identifiers": self.device_unique_id},
                    "value_template": "{{value_json.decimal_digit}}",
                },
            },
            {
                "name": "decimal_uom",
                "payload": {
                    "name": "decimal uom",
                    "device_class": None,
                    "unique_id": f"decimal_uom{self.device_unique_id}",
                    "state_topic": self.topic_state,
                    "device": {"identifiers": self.device_unique_id},
                    "value_template": "{{value_json.decimal_uom}}",
                },
            },
            {
                "name": "right_number_to_liters",
                "payload": {
                    "name": "right number to liters",
                    "device_class": None,
                    "unique_id": f"right_number_to_liters{self.device_unique_id}",
                    "state_topic": self.topic_state,
                    "device": {"identifiers": self.device_unique_id},
                    "value_template": "{{value_json.right_number_to_liters}}",
                },
            },
            {
                "name": "main_uom",
                "payload": {
                    "name": "main uom",
                    "device_class": None,
                    "unique_id": f"main_uom{self.device_unique_id}",
                    "state_topic": self.topic_state,
                    "device": {"identifiers": self.device_unique_id},
                    "value_template": "{{value_json.main_uom}}",
                },
            },
            {
                "name": "rotate",
                "payload": {
                    "name": "rotate",
                    "device_class": None,
                    "unique_id": f"rotate{self.device_unique_id}",
                    "state_topic": self.topic_state,
                    "device": {"identifiers": self.device_unique_id},
                    "value_template": "{{value_json.rotate}}",
                },
            },
        ]
        global_result = []

        for s in sensors:
            name = s.get("name")
            payload = s.get("payload")
            pub = self.publish_payload(
                topic=f"{self.topic}/{name}/config",
                payload=json.dumps(payload),
                qos=0,
                retain=True,
            )
            global_result.append({name: pub.is_published()})

        # Register one camera entity per pipeline frame slot
        device_ref = {
            "identifiers": self.device_unique_id,
            "name": self.name,
            "manufacturer": "eaubbies project",
            "model": "V1",
        }
        for slug, label in FRAME_SLOTS:
            cam_cfg = {
                "name": f"{self.name} {label}",
                "unique_id": f"frame_{slug}_{self.device_unique_id}",
                "topic": self._camera_image_topic(slug),
                "device": device_ref,
            }
            pub = self.publish_payload(
                topic=self._camera_config_topic(slug),
                payload=json.dumps(cam_cfg),
                qos=0,
                retain=True,
            )
            global_result.append({f"camera_{slug}": pub.is_published()})
            logger.info(f"Camera entity registered: {slug}")

        logger.info(f"MQTT device publish results: {global_result}")
        return global_result

    # ------------------------------------------------------------------
    # state publishing
    # ------------------------------------------------------------------

    def send_value(self, values: dict):
        if values:
            response = self.publish_payload(
                topic=self.topic_state, payload=json.dumps(values)
            )
            return response
        raise ValueError("Values is Null or None")

    def send_frame(self, slug: str, image_path: str):
        """Publish a JPEG file as raw bytes to the camera topic for *slug*."""
        if not image_path or not os.path.exists(image_path):
            logger.warning(
                f"send_frame [{slug}]: image not found at '{image_path}' — skipping"
            )
            return None
        with open(image_path, "rb") as fh:
            jpeg_bytes = fh.read()
        topic = self._camera_image_topic(slug)
        logger.info(f"Publishing frame [{slug}] ({len(jpeg_bytes)} bytes) to {topic}")
        response = self.publish_payload(
            topic=topic, payload=jpeg_bytes, qos=0, retain=True
        )
        logger.info(f"Frame [{slug}] publish result: {response.is_published()}")
        return response

    def send_all_frames(self, frames: dict):
        """
        Publish every available frame.

        *frames* is a dict mapping slug -> absolute file path, e.g.::

            {
                "source":     "/path/static/img/frames/0.frame_origine.jpg",
                "final":      "/path/static/img/frames/8.frame_final.jpg",
                "ocr_boxes":  "/path/static/img/frames/10.ocr_boxes.jpg",
                "contrast":   "/path/static/img/frames/5.contrast.jpg",
                ...
            }

        Slugs not in *frames* (pipeline steps that were inactive) are silently skipped.
        """
        results = {}
        for slug, path in frames.items():
            results[slug] = self.send_frame(slug=slug, image_path=path)
        logger.info(
            f"send_all_frames complete — {len(results)} frame(s) published: {list(results.keys())}"
        )
        return results
