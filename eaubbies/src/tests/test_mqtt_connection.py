# eaubbies/eaubbies/src/tests/test_mqtt_connection.py
"""Tests for MQTT connection-status reporting in :mod:`utils.mqtt`.

These cover the new behaviour that a non-responding / misconfigured broker is
reported via ``connected`` / ``connection_error`` instead of silently failing,
so the service layer can still return the computed reading with a warning.
"""

import types

import pytest

import utils.mqtt as mqtt_module
from utils.mqtt import MqttCLient


@pytest.fixture
def patched_config(monkeypatch):
    """Provide a deterministic YamlConfigLoader for MqttCLient construction."""

    def _make(mqtt_conf):
        class _Loader:
            def __init__(self, *args, **kwargs):
                self.data = {"mqtt": mqtt_conf}

            def set_param(self, *keys, value=None):
                # unique_id is already provided, so this should not be needed.
                pass

        monkeypatch.setattr(mqtt_module, "YamlConfigLoader", _Loader)

    return _make


def _base_conf(**overrides):
    conf = {
        "server": "broker.local",
        "port": 1883,
        "device": {"unique_id": "abc123", "name": "watermeter"},
        "sensors": {"water": {"unit_of_measurement": "l"}},
        "discovery_prefix": "homeassistant",
    }
    conf.update(overrides)
    return conf


def test_missing_server_reports_not_configured(patched_config, monkeypatch):
    """No server configured -> not connected with a clear message."""
    patched_config(_base_conf(server=None))
    client = MqttCLient()
    assert client.connected is False
    assert "not configured" in client.connection_error.lower()


def test_unreachable_broker_reports_not_responding(patched_config, monkeypatch):
    """A broker that never sends CONNACK -> 'not responding' after timeout."""
    patched_config(_base_conf())

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def enable_logger(self, logger):
            pass

        def username_pw_set(self, username, password):
            pass

        def connect(self, host, port):
            # Simulate a socket connect that succeeds but no CONNACK arrives.
            return None

        def loop_start(self):
            pass

    monkeypatch.setattr(mqtt_module, "Client", lambda *a, **k: _FakeClient())

    client = MqttCLient.__new__(MqttCLient)
    client.config_loader = types.SimpleNamespace(set_param=lambda *a, **k: None)
    client.configuration = _base_conf()
    client.connected = False
    client.connection_error = None
    # Use a short timeout to keep the test fast.
    client.mqtt_connection(connect_timeout=0.2)

    assert client.connected is False
    assert "not responding" in client.connection_error.lower()


def test_connect_exception_reports_not_responding(patched_config, monkeypatch):
    """A refused/failed connect() -> not connected with an error message."""
    patched_config(_base_conf())

    class _BoomClient:
        def __init__(self, *args, **kwargs):
            pass

        def enable_logger(self, logger):
            pass

        def username_pw_set(self, username, password):
            pass

        def connect(self, host, port):
            raise ConnectionRefusedError("connection refused")

        def loop_start(self):
            pass

    monkeypatch.setattr(mqtt_module, "Client", lambda *a, **k: _BoomClient())

    client = MqttCLient.__new__(MqttCLient)
    client.config_loader = types.SimpleNamespace(set_param=lambda *a, **k: None)
    client.configuration = _base_conf()
    client.connected = False
    client.connection_error = None
    client.mqtt_connection(connect_timeout=0.2)

    assert client.connected is False
    assert "not responding" in client.connection_error.lower()


def test_on_connect_success_sets_connected():
    """A successful CONNACK (rc=0) flips connected to True."""
    client = MqttCLient.__new__(MqttCLient)
    client.connected = False
    client.connection_error = "stale"
    client.on_connect(None, None, None, 0)
    assert client.connected is True
    assert client.connection_error is None


def test_on_connect_refused_sets_error():
    """A refused CONNACK (rc!=0) records an error and stays disconnected."""
    client = MqttCLient.__new__(MqttCLient)
    client.connected = False
    client.connection_error = None
    client.on_connect(None, None, None, 5)
    assert client.connected is False
    assert client.connection_error is not None
