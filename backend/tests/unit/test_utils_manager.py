import pytest
from app.services.utils_manager import UtilsManager

class MockAnalyzer:
    pass

@pytest.fixture
def manager():
    analyzer = MockAnalyzer()
    return UtilsManager(analyzer)

def test_extract_dimension_value_mm(manager):
    assert abs(manager.extract_dimension_value("200mm") - 0.2) < 1e-6

def test_extract_dimension_value_meter(manager):
    assert abs(manager.extract_dimension_value("2.5") - 2.5) < 1e-6

def test_calculate_area(manager):
    assert manager.calculate_area("板", 2, 3, 0, 0) == 6
    assert manager.calculate_area("墙", 2, 0, 3, 0) == 6
    assert manager.calculate_area("梁", 0, 2, 3, 0) == 6
    assert manager.calculate_area("柱", 0, 2, 3, 0) == 6
    assert manager.calculate_area("未知", 2, 3, 4, 0) == 12

def test_calculate_volume(manager):
    assert manager.calculate_volume("板", 2, 3, 0, 0.1) == 0.6
    assert manager.calculate_volume("墙", 2, 0, 3, 0.1) == 0.6
    assert manager.calculate_volume("梁", 2, 3, 4, 0) == 24
    assert manager.calculate_volume("柱", 0, 2, 3, 4) == 24
    assert manager.calculate_volume("未知", 2, 3, 4, 5) == 120

def test_format_dimensions(manager):
    assert manager.format_dimensions(2, 3, 4, 0.1).startswith("L2000")
    assert manager.format_dimensions(0, 0, 0, 0) == "-" 