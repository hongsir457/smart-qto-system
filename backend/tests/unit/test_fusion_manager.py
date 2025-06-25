import pytest
from app.services.fusion_manager import FusionManager

class MockAnalyzer:
    def __init__(self):
        self.slice_components = {"0_0": [], "0_1": []}
        self.enhanced_slices = []
        self.coordinate_service = type("Coord", (), {"slice_coordinate_map": {}})()
        self.merged_components = []

@pytest.fixture
def manager():
    analyzer = MockAnalyzer()
    return FusionManager(analyzer)

def test_find_enhanced_slice_info_none(manager):
    assert manager.find_enhanced_slice_info("0_0") is None 