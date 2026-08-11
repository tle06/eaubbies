import sys
import os
import pytest
from utils.tesseract_client import TesseractClient
from utils.utils import volume_converter, generate_result

# Add eaubbies/src to sys.path so we can import utils and modules directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def test_volume_converter():
    # Test identical unit conversion
    assert volume_converter(100, "l", "l") == 100
    # Test liters to cl
    assert volume_converter(10, "l", "cl") == 1000
    # Test m3 to liters
    assert volume_converter(1, "m3", "l") == 1000
    # Test invalid unit error
    with pytest.raises(ValueError):
        volume_converter(100, "unknown_unit", "l")


def test_tesseract_client_mock():
    # Since tesseract might not be installed on the local system where tests are run (e.g. macOS host dev environment vs container)
    # we can create a simple frame and mock or verify if we can instantiate it.
    client = TesseractClient()
    assert client is not None


def test_generate_result_all(monkeypatch):
    # Mock YamlConfigLoader to return deterministic configuration values
    class MockConfigLoader:
        def __init__(self, *args, **kwargs):
            self.data = {}

        def get_param(self, *keys):
            if keys == ("vision", "integer", "digit"):
                return 6
            elif keys == ("vision", "integer", "unit_of_measurement"):
                return "m3"
            elif keys == ("vision", "decimal", "digit"):
                return 5
            elif keys == ("vision", "decimal", "unit_of_measurement"):
                return "cl"
            elif keys == ("vision", "coordinates"):
                return {
                    "integer": {"active": False},
                    "digit": {"active": False},
                    "all": {"active": True},
                }
            elif keys == ("mqtt", "sensors", "water", "unit_of_measurement"):
                return "l"
            elif keys == ("vision", "rotate"):
                return 0.0
            raise ValueError(f"Unknown key: {keys}")

    monkeypatch.setattr("utils.configuration.YamlConfigLoader", MockConfigLoader)

    # test result logic with dotted string
    res = generate_result("123456.789")
    assert res["left_number"] == 123456
    assert res["right_number"] == 789
    # 123456 m3 = 123456000 l; 789 cl = 7.89 l => Total = 123456007.89 l
    assert res["total_liters"] == 123456007.89


def test_generate_result_integer_only(monkeypatch):
    class MockConfigLoaderIntegerOnly:
        def __init__(self, *args, **kwargs):
            self.data = {}

        def get_param(self, *keys):
            if keys == ("vision", "integer", "digit"):
                return 6
            elif keys == ("vision", "integer", "unit_of_measurement"):
                return "m3"
            elif keys == ("vision", "decimal", "digit"):
                return 5
            elif keys == ("vision", "decimal", "unit_of_measurement"):
                return "cl"
            elif keys == ("vision", "coordinates"):
                return {
                    "integer": {"active": True},
                    "digit": {"active": False},
                    "all": {"active": False},
                }
            elif keys == ("mqtt", "sensors", "water", "unit_of_measurement"):
                return "l"
            elif keys == ("vision", "rotate"):
                return 0.0
            raise ValueError(f"Unknown key: {keys}")

    monkeypatch.setattr(
        "utils.configuration.YamlConfigLoader", MockConfigLoaderIntegerOnly
    )

    # OCR reads only integer coordinates
    res = generate_result("001234")
    assert res["left_number"] == 1234
    assert res["right_number"] == 0


def _all_mode_config():
    """Return a MockConfigLoader class configured for the 'all' region mode."""

    class MockConfigLoaderAll:
        def __init__(self, *args, **kwargs):
            self.data = {}

        def get_param(self, *keys):
            if keys == ("vision", "integer", "digit"):
                return 6
            elif keys == ("vision", "integer", "unit_of_measurement"):
                return "m3"
            elif keys == ("vision", "decimal", "digit"):
                return 5
            elif keys == ("vision", "decimal", "unit_of_measurement"):
                return "cl"
            elif keys == ("vision", "coordinates"):
                return {
                    "integer": {"active": False},
                    "digit": {"active": False},
                    "all": {"active": True},
                }
            elif keys == ("mqtt", "sensors", "water", "unit_of_measurement"):
                return "l"
            elif keys == ("vision", "rotate"):
                return 0.0
            raise ValueError(f"Unknown key: {keys}")

    return MockConfigLoaderAll


def test_generate_result_no_dot_splits_by_integer_digits(monkeypatch):
    """Without a dot, the left number uses the configured integer digit count.

    NOTE: the current implementation derives the right number as
    ``raw[len(raw) - integer_digit:]`` (start index), not the trailing
    ``decimal_digit`` characters. This test documents the *actual* behaviour;
    see the review notes for the latent parsing bug this exposes.
    """
    monkeypatch.setattr("utils.configuration.YamlConfigLoader", _all_mode_config())
    res = generate_result("123456789")
    assert res["left_number"] == 123456
    # Right number = int("123456789"[3:]) with the current slicing logic.
    assert res["right_number"] == 456789


def test_generate_result_strips_spaces(monkeypatch):
    """Spaces produced by OCR are removed before parsing."""
    monkeypatch.setattr("utils.configuration.YamlConfigLoader", _all_mode_config())
    res = generate_result("12 34 56")
    assert res["raw_result_without_space"] == "123456"


def test_generate_result_bad_dotted_value_raises(monkeypatch):
    """A dotted value whose parts are not integers raises ValueError."""
    monkeypatch.setattr("utils.configuration.YamlConfigLoader", _all_mode_config())
    with pytest.raises(ValueError):
        generate_result("12.ab")
