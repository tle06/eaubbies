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

        global_result = []
        payload_water = {
            "name": "watermeter",
            "device_class": "water",
            "unique_id": f"water_{self.device_unique_id}",
            "state_topic": self.topic_state,
            "device": {
                "identifiers": self.device_unique_id,
                "name": self.name,
                "manufacturer": "eaubbies project",
                "model": "V1",
            },
            "unit_of_measurement": self.sensor_water_uom,
            "value_template": "{{value_json.water}}",
        }

        result_water = self.publish_payload(
            topic=f"{self.topic}/watermeter/config",
            payload=json.dumps(payload_water),
            qos=0,
            retain=True,
        )

        global_result.append({"water": result_water.is_published()})
        payload_raw = {
            "name": "raw value",
            "device_class": None,
            "unique_id": f"raw_{self.device_unique_id}",
            "state_topic": self.topic_state,
            "device": {"identifiers": self.device_unique_id},
            "value_template": "{{value_json.raw}}",
        }

        result_raw = self.publish_payload(
            topic=f"{self.topic}/rawvalue/config",
            payload=json.dumps(payload_raw),
            qos=0,
            retain=True,
        )
        global_result.append({"raw": result_raw.is_published()})
        return global_result

    def send_value(self, value, measurement: str):

        if value:
            payload = {measurement: value}
            response = self.publish_payload(
                topic=self.topic_state, payload=json.dumps(payload)
            )
            return response

        raise ValueError("Value is Null or None")
