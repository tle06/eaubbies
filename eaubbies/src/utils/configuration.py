import yaml
import os
from utils.utils import generate_unique_id

default_config_file = "data/config/main.yaml"


class YamlConfigLoader:

    def __init__(self, filename=None):
        self.filename = filename or default_config_file
        self.data = self.load_config()

    def load_config(self):
        if not os.path.exists(self.filename) or os.path.getsize(self.filename) == 0:
            os.makedirs(os.path.dirname(self.filename), exist_ok=True)
            default_config = self.generate_default_config()

            with open(self.filename, "w") as file:
                yaml.dump(default_config, file)
            return default_config
        try:
            with open(self.filename, "r") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Config file '{self.filename}' not found.")

    def generate_default_config(self):
        # Modify this dictionary according to your default configuration
        default_config = {
            "frame": {
                "storage_path": "static/img/frames",
            },
            "result": {"current": None, "previous": None, "unit": "l"},
            "vision": {
                "counter": 0,
                "rotate": 0.0,
                "endpoint": None,
                "key": None,
                "line_with_data": 0,
                "region": {"current": None, "previous": None},
                "integer": {"digit": 6, "unit_of_measurement": "m3"},
                "decimal": {"digit": 5, "unit_of_measurement": "cl"},
                "coordinates": {
                    "active": False,
                    "all": {"height": None, "width": None, "x": None, "y": None},
                    "digit": {"height": None, "width": None, "x": None, "y": None},
                    "integer": {"height": None, "width": None, "x": None, "y": None},
                },
            },
            "rtsp": {
                "url": None,
                "image": {
                    "contrast": {"active": False, "alpha": 1.2, "beta": 1},
                    "convert_to_bgr": True,
                    "convert_to_grey": False,
                    "exposure": {
                        "active": True,
                        "in_range": [0, 129],
                        "out_range": [0, 255],
                    },
                    "fill_image": {"active": True, "coordinates": "integer"},
                    "sharpen": {"active": False, "amount": 30, "threshold": 3},
                },
            },
            "mqtt": {
                "server": None,
                "user": None,
                "password": None,
                "discovery_prefix": "homeassistant",
                "sensors": {"water": {"unit_of_measurement": "l"}},
                "device": {
                    "name": "eaubbies-watermeter",
                    "node_id": "eaubbies-watermeter",
                    "unique_id": generate_unique_id(),
                },
            },
            "service": {"cron": "01:00", "counter": 0},
        }

        return default_config

    def get_param(self, *keys):
        current_level = self.data
        for key in keys:
            if key not in current_level:
                raise ValueError(f"Param '{key}' not found in the config file.")
            current_level = current_level[key]
        return current_level

    def set_param(self, *keys, value):
        current_level = self.data
        for key in keys[:-1]:
            if key not in current_level:
                current_level[key] = {}
            current_level = current_level[key]
        current_level[keys[-1]] = value
        with open(self.filename, "w") as file:
            yaml.dump(self.data, file)
