# eaubbies/eaubbies/src/tests/test_save_config_result.py
"""Tests for editing the previous/current meter values via /save_config.

Covers the new "Meter values" section: valid floats persist, an empty field
resets to None, and an unparseable value is ignored (never corrupts the stored
reading).
"""

import pytest

app_module = pytest.importorskip("app", reason="app module could not import")
from utils.configuration import YamlConfigLoader  # noqa: E402


@pytest.fixture
def client():
    """A Flask test client for the app."""
    return app_module.app.test_client()


def test_set_previous_and_current_and_unit(client):
    """Valid values are stored as floats and the unit is lower-cased."""
    client.post(
        "/save_config",
        data={
            "result_previous": "100.5",
            "result_current": "101.25",
            "result_unit": "M3",
        },
    )
    cfg = YamlConfigLoader()
    assert cfg.get_param("result", "previous") == 100.5
    assert cfg.get_param("result", "current") == 101.25
    assert cfg.get_param("result", "unit") == "m3"


def test_empty_value_resets_to_none(client):
    """Submitting an empty field clears the stored value."""
    client.post(
        "/save_config",
        data={"result_previous": "50", "result_current": "60"},
    )
    client.post(
        "/save_config",
        data={"result_previous": "", "result_current": "60"},
    )
    cfg = YamlConfigLoader()
    assert cfg.get_param("result", "previous") is None
    assert cfg.get_param("result", "current") == 60.0


def test_invalid_value_is_ignored(client):
    """An unparseable value leaves the existing reading untouched."""
    client.post("/save_config", data={"result_current": "77.7"})
    client.post("/save_config", data={"result_current": "not-a-number"})
    cfg = YamlConfigLoader()
    assert cfg.get_param("result", "current") == 77.7
