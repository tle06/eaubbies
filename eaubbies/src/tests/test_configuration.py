# eaubbies/eaubbies/src/tests/test_configuration.py
"""Tests for :mod:`utils.configuration`.

Focus areas:
* first-run default generation writes a usable config,
* ``get_param`` / ``set_param`` round-trip and raise on unknown keys,
* ``_atomic_write`` is durable and leaves no temp files behind, and
* a failure during serialisation does not corrupt an existing config.
"""

import os

import pytest

from utils.configuration import YamlConfigLoader


def test_first_run_generates_default_config(tmp_path):
    """A missing config file is created with default contents."""
    cfg_file = tmp_path / "eaubbies" / "main.yaml"
    loader = YamlConfigLoader(filename=str(cfg_file))
    assert cfg_file.exists()
    assert loader.get_param("vision", "engine") == "azure"
    assert loader.get_param("service", "counter") == 0


def test_set_param_persists_and_reloads(tmp_path):
    """A value set through one loader is visible to a fresh loader."""
    cfg_file = tmp_path / "eaubbies" / "main.yaml"
    loader = YamlConfigLoader(filename=str(cfg_file))
    loader.set_param("vision", "counter", value=42)

    reloaded = YamlConfigLoader(filename=str(cfg_file))
    assert reloaded.get_param("vision", "counter") == 42


def test_set_param_creates_missing_intermediate_keys(tmp_path):
    """set_param builds intermediate dicts for previously-absent paths."""
    cfg_file = tmp_path / "eaubbies" / "main.yaml"
    loader = YamlConfigLoader(filename=str(cfg_file))
    loader.set_param("brand", "new", "leaf", value="ok")
    assert loader.get_param("brand", "new", "leaf") == "ok"


def test_get_param_unknown_key_raises(tmp_path):
    """Unknown keys raise ValueError rather than KeyError."""
    cfg_file = tmp_path / "eaubbies" / "main.yaml"
    loader = YamlConfigLoader(filename=str(cfg_file))
    with pytest.raises(ValueError):
        loader.get_param("does", "not", "exist")


def test_atomic_write_leaves_no_temp_files(tmp_path):
    """After writes, only the target file remains in the directory."""
    cfg_file = tmp_path / "eaubbies" / "main.yaml"
    loader = YamlConfigLoader(filename=str(cfg_file))
    loader.set_param("vision", "counter", value=7)

    directory = os.path.dirname(str(cfg_file))
    leftovers = [f for f in os.listdir(directory) if f.endswith(".tmp")]
    assert leftovers == []


def test_atomic_write_failure_preserves_existing_file(tmp_path, monkeypatch):
    """A serialisation error must not destroy the previously-valid config."""
    cfg_file = tmp_path / "eaubbies" / "main.yaml"
    loader = YamlConfigLoader(filename=str(cfg_file))
    original = cfg_file.read_text()

    # Force the YAML serialisation to fail mid-write.
    import utils.configuration as configuration_module

    def _boom(*args, **kwargs):
        raise RuntimeError("dump failed")

    monkeypatch.setattr(configuration_module.yaml, "dump", _boom)

    with pytest.raises(RuntimeError):
        loader._atomic_write(str(cfg_file), {"any": "data"})

    # The on-disk file is untouched and no temp files remain.
    assert cfg_file.read_text() == original
    directory = os.path.dirname(str(cfg_file))
    assert [f for f in os.listdir(directory) if f.endswith(".tmp")] == []
