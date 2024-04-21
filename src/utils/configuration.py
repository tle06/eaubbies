import yaml
import os

default_config_file = "data/config/main.yaml"


class YamlConfigLoader:

    def __init__(self, filename=None):
        self.filename = filename or default_config_file
        self.data = self.load_config()

    def load_config(self):
        if not os.path.exists(self.filename):
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
                "exposure": None,
                "brightness": None,
            },
            "result": {"current": None, "previous": None, "unit": "l"},
            "vision": {
                "endpoint": None,
                "key": None,
                "previous_region": None,
                "curent_region": None,
            },
            "rtsp": {"url": None},
            "mqtt": {"server": None, "user": None, "password": None},
            "service": {"cron": None},
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
