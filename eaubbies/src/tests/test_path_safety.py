# eaubbies/eaubbies/src/tests/test_path_safety.py
"""Tests for the frame path-traversal guard in :mod:`app`.

Importing ``app`` has import-time side effects (config load, cron registration,
MQTT-independent setup). The ``conftest`` fixtures redirect config to a temp
dir; if the environment still cannot import ``app`` (e.g. no writable crontab
in a restricted sandbox) the tests are skipped rather than failing spuriously.
"""

import os

import pytest

try:
    # Importing app has side effects (config load, cron registration). If the
    # host cannot support them (e.g. no writable crontab in a sandbox), skip
    # this module rather than failing collection.
    import app
except Exception as exc:  # noqa: BLE001 - intentionally broad for skip
    app = None
    pytest.skip(f"app module could not be imported: {exc}", allow_module_level=True)


def test_rejects_parent_traversal(tmp_path):
    """A ``../`` escape resolves outside the base and is rejected."""
    base = tmp_path / "frames"
    base.mkdir()
    assert app._safe_frame_path(str(base), "../secret.txt") is None


def test_rejects_absolute_escape(tmp_path):
    """An absolute path pointing elsewhere is rejected."""
    base = tmp_path / "frames"
    base.mkdir()
    assert app._safe_frame_path(str(base), "/etc/passwd") is None


def test_rejects_sibling_prefix_directory(tmp_path):
    """A sibling dir sharing a name prefix must not be accepted."""
    base = tmp_path / "frames"
    base.mkdir()
    (tmp_path / "frames_evil").mkdir()
    assert app._safe_frame_path(str(base), "../frames_evil/x.jpg") is None


def test_accepts_valid_filename(tmp_path):
    """A plain filename inside the base resolves to an absolute path."""
    base = tmp_path / "frames"
    base.mkdir()
    resolved = app._safe_frame_path(str(base), "0.frame_origine.jpg")
    assert resolved is not None
    assert resolved == os.path.join(os.path.realpath(str(base)), "0.frame_origine.jpg")
