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
