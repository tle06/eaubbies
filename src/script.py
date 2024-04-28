from service import service_process, configuration
from utils.mqtt import MqttCLient
import json
import paho.mqtt.client as mqtt

# data = json.loads(service_process())
# print(data.get("result"))
# raw_value = data.get("result").get("raw_result_without_space")

mqtt_user = configuration.get_param("mqtt", "user")
mqtt_password = configuration.get_param("mqtt", "password")
mqtt_server = configuration.get_param("mqtt", "server")
mqtt_port = configuration.get_param("mqtt", "port")

client_mqtt = MqttCLient()

client_mqtt.mqtt_publish_device()
client_mqtt.send_value(value=104, measurement="water")
client_mqtt.send_value(value=800, measurement="raw")


# previous_value = configuration.get_param("result", "previous")
# if previous_value:
#     if total_liters > previous_value:
#         print(f"total liter ({total_liters}) is > previous value ({previous_value})")
#         configuration.set_param("result", "previous", value=total_liters)
#         configuration.set_param("result", "current", value=total_liters)
# else:
#     print("no previous value")
#     configuration.set_param("result", "previous", value=total_liters)
#     configuration.set_param("result", "current", value=total_liters)
