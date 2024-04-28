from service import service_process, configuration
from utils.mqtt import MqttCLient
from utils.utils import volume_converter, generate_result
import json
import paho.mqtt.client as mqtt

# data = json.loads(service_process())

raw_result = "00009086510"
result = generate_result(raw_result=raw_result)
print(result)
client_mqtt = MqttCLient()
client_mqtt.mqtt_publish_device()
client_mqtt.send_value(values=result)
