import yaml
import os
import tempfile
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
    """
    Load and persist the add-on runtime configuration as a YAML file.

    The configuration path is resolved from ``CONFIG_PATH`` (``/config`` inside
    Home Assistant, ``/data`` standalone) so it lives on a persistent, mounted
    volume and therefore survives container restarts/reboots. All writes go
    through :meth:`_atomic_write` so a crash or power loss mid-write cannot
    leave a truncated/corrupt config behind.
    """

    default_config_file = env.str(
        "DEFAULT_CONFIG_FILE",
        os.path.join(_config_base, "eaubbies", "main.yaml"),
    )
    default_frames_path = env.str(
        "DEFAULT_FRAMES_PATH",
        os.path.join(_config_base, "eaubbies", "img", "frames"),
    )

    def __init__(self, filename=None):
        """
        Parameters:
            filename (str): Optional override for the config file path. Defaults
                to :attr:`default_config_file`.
        """
        self.filename = filename or self.default_config_file
        self.data = self.load_config()

    @staticmethod
    def _atomic_write(filename: str, data: dict):
        """
        Write *data* to *filename* atomically and durably.

        Serialises to a temporary file in the same directory, flushes and
        ``fsync``s it, then ``os.replace``s it over the target. ``os.replace``
        is atomic on POSIX, so readers always see either the old or the new
        complete file — never a partially written one. This prevents config
        corruption on power loss, which is the realistic failure mode for a
        Home Assistant box that reboots unexpectedly.

        Parameters:
            filename (str): Destination config path.
            data (dict): Configuration mapping to serialise as YAML.
        """
        directory = os.path.dirname(filename) or "."
        os.makedirs(directory, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=directory, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as tmp_file:
                yaml.dump(data, tmp_file)
                tmp_file.flush()
                os.fsync(tmp_file.fileno())
            os.replace(tmp_path, filename)
        except Exception:
            # Never leave a stray temp file behind on failure.
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise

    def load_config(self):
        """
        Load the config from disk, generating defaults on first run.

        If the file is missing or empty, a default configuration is generated
        and written atomically. Otherwise the existing YAML is parsed and
        returned.

        Returns:
            dict: The loaded (or freshly generated) configuration.
        """
        if not os.path.exists(self.filename) or os.path.getsize(self.filename) == 0:
            default_config = self.generate_default_config()
            self._atomic_write(self.filename, default_config)
            return default_config
        try:
            with open(self.filename, "r") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Config file '{self.filename}' not found.")

    def generate_default_config(self):
        """
        Build the default configuration dictionary used on first launch.

        Returns:
            dict: A fully-populated default configuration.
        """
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
        """
        Return a nested configuration value by walking *keys*.

        Parameters:
            *keys: Ordered dictionary keys to traverse (e.g. ``"vision",
                "engine"``).

        Returns:
            The value stored at the requested path.

        Raises:
            ValueError: If any key in the path is missing.
        """
        current_level = self.data
        for key in keys:
            if key not in current_level:
                raise ValueError(f"Param '{key}' not found in the config file.")
            current_level = current_level[key]
        return current_level

    def set_param(self, *keys, value):
        """
        Set a nested configuration value and persist it atomically.

        Intermediate dictionaries are created as needed. The whole config is
        re-serialised through :meth:`_atomic_write` so the on-disk file is never
        left partially written.

        Parameters:
            *keys: Ordered dictionary keys identifying the target location.
            value: Value to store at ``keys[-1]``.
        """
        current_level = self.data
        for key in keys[:-1]:
            if key not in current_level:
                current_level[key] = {}
            current_level = current_level[key]
        current_level[keys[-1]] = value
        self._atomic_write(self.filename, self.data)
