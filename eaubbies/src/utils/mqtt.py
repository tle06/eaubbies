from paho.mqtt.client import Client, CallbackAPIVersion
from utils.configuration import YamlConfigLoader
from utils.utils import generate_unique_id
import logging
import json
import time


logging.basicConfig(level=logging.INFO)


class MqttCLient:

    def __init__(self):
        self.config_loader = YamlConfigLoader()
        self.configuration = self.config_loader.data
        self.configuration = self.configuration.get("mqtt")

        self.device_config = self.configuration.get("device")
        self.sensors_config = self.configuration.get("sensors")

        self.discovery_prefix = self.configuration.get("discovery_prefix")
        self.name = self.device_config.get("name")
        self.sensor_water_uom = self.sensors_config.get("water").get(
            "unit_of_measurement"
        )

        self.device_unique_id = self.get_device_unique_id()
        self.topic = f"{self.discovery_prefix}/sensor/{self.name}"
        self.topic_config = topic = f"{self.topic}/watermeter/config"
        self.topic_state = topic = f"{self.topic}/watermeter/state"

        self.mqtt_connection()

    def mqtt_connection(self):

        mqtt_user = self.configuration.get("user")
        mqtt_password = self.configuration.get("password")
        mqtt_server = self.configuration.get("server")
        mqtt_port = self.configuration.get("port")
        mqtt_url = self.configuration.get("server")
        self.client = Client(CallbackAPIVersion.VERSION2)
        self.client.enable_logger()
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.subscribe = self.subscribe
        self.client.username_pw_set(username=mqtt_user, password=mqtt_password)
        self.client.on_disconnect
        self.client.connect(host=mqtt_url, port=mqtt_port)
        return

    def get_device_unique_id(self):
        unique_id = unique_id = self.device_config.get("unique_id")
        if not unique_id:
            print("generate unique ID")
            unique_id = generate_unique_id()
            self.config_loader.set_param("mqtt", "device", "unique_id", value=unique_id)
            print(unique_id)
        return unique_id

    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            print("Unexpected disconnection.")

    def on_connect(self, client, userdata, flags, rc):
        print(client, userdata, flags, rc)
        if rc == 0:
            print("connected OK Returned code=", rc, flush=True)
        else:
            print("Bad connection Returned code=", rc, flush=True)

    def on_message(self, client, userdata, message):
        msg_str = message.payload.decode("utf-8")
        print("message received : ", str(msg_str))
        print("message topic : ", message.topic)

    def subscribe(self):
        self.client.loop_forever()

    def on_disconnect(self, client, userdata, rc=0):
        self.client.loop_stop()

    def publish_payload(
        self, topic: str, payload: dict, qos: int = 0, retain: bool = True
    ):
        print(payload)
        response = self.client.publish(
            topic=topic, payload=payload, qos=qos, retain=retain
        )
        print(f"response is_published: {response.is_published()}")
        return response

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
                    "device": {
                        "identifiers": self.device_unique_id,
                    },
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
        print(global_result)

        return global_result

    def send_value(self, values: dict):

        if values:
            response = self.publish_payload(
                topic=self.topic_state, payload=json.dumps(values)
            )
            return response

        raise ValueError("Values is Null or None")
