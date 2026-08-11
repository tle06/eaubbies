# eaubbies/eaubbies/src/tests/test_utils.py
"""Tests for pure helpers in :mod:`utils.utils`."""

import pytest

from utils.utils import (
    volume_converter,
    time_to_cron,
    generate_unique_id,
)


@pytest.mark.parametrize(
    "number,from_unit,to_unit,expected",
    [
        (1, "m3", "l", 1000),
        (100, "cl", "l", 1.0),
        (1, "hl", "l", 100),
        (5, "dl", "l", 0.5),
        (3, "l", "l", 3),
    ],
)
def test_volume_converter_units(number, from_unit, to_unit, expected):
    """Conversions across all supported units are correct."""
    assert volume_converter(number, from_unit, to_unit) == expected


def test_volume_converter_invalid_unit():
    """Unknown units raise ValueError."""
    with pytest.raises(ValueError):
        volume_converter(1, "l", "gallon")


@pytest.mark.parametrize(
    "time_str,expected",
    [
        ("01:30", "30 1 * * *"),
        ("00:15", "15 * * * *"),  # hour 0 -> every hour
        ("06:00", "* 6 * * *"),  # minute 0 -> every minute
        ("00:00", "* * * * *"),
    ],
)
def test_time_to_cron(time_str, expected):
    """HH:MM is mapped to the expected cron expression."""
    assert time_to_cron(time_str) == expected


def test_generate_unique_id_is_short_and_unique():
    """IDs are 8 hex chars and differ across calls."""
    a = generate_unique_id()
    b = generate_unique_id()
    assert len(a) == 8
    assert a != b
