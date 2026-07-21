import yaml
import os
from utils.utils import generate_unique_id
from environs import Env

env = Env()
env.read_env()

# CONFIG_PATH is set by the entrypoint:
#   /config  when running as an HA add-on (Supervisor mounts the share there)
#   /data    when running standalone (docker-compose mounts the volume there)
# Falls back to /config so existing HA deployments are unaffected.
_config_base = env.str("CONFIG_PATH", "/config")


class YamlConfigLoader:
    default_config_file = env.str(
        "DEFAULT_CONFIG_FILE",
        os.path.join(_config_base, "eaubbies", "main.yaml"),
    )
    default_frames_path = env.str(
        "DEFAULT_FRAMES_PATH",
        os.path.join(_config_base, "eaubbies", "img", "frames"),
    )

    def __init__(self, filename=None):
        self.filename = filename or self.default_config_file
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
                "storage_path": self.default_frames_path,
            },
            "result": {"current": None, "previous": None, "unit": "l"},
            "vision": {
                "engine": "azure",  # Option between 'azure' or 'tesseract'
                "tesseract_cmd": None,
                "tesseract_config": "--psm 7 --oem 1 -c tessedit_char_whitelist=0123456789.",
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
                    "contrast": {"active": False, "alpha": 1.5, "beta": 15},
                    "convert_to_bgr": False,
                    "convert_to_grey": True,
                    "exposure": {
                        "active": False,
                        "in_range": [50, 200],
                        "out_range": [0, 255],
                    },
                    "crop_image": {"active": True, "coordinates": "integer"},
                    "sharpen": {"active": False, "amount": 3.0, "threshold": 0},
                },
            },
            "mqtt": {
                "server": None,
                "port": 1883,
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
            "setup": {"init_config": False},
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
