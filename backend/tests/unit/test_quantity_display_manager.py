import pytest
from app.services.quantity_display_manager import QuantityDisplayManager

class MockUtilsManager:
    def extract_dimension_value(self, v):
        return 1.0
    def calculate_area(self, *a):
        return 2.0
    def calculate_volume(self, *a):
        return 3.0
    def format_dimensions(self, *a):
        return "L1000×W1000"

class MockComp:
    def __init__(self):
        self.id = "C1"
        self.type = "梁"
        self.material = "C30"
        self.geometry = {"dimensions": {"length": "1", "width": "1", "height": "1", "thickness": "1"}}
        self.structural_role = "承重"
        self.connections = ["C2"]
        self.location = "A区"
        self.confidence = 0.9
        self.source_block = "0_0"

class MockAnalyzer:
    def __init__(self):
        self.merged_components = [MockComp()]
        self.utils_manager = MockUtilsManager()
        self.global_drawing_overview = {"drawing_info": {"name": "test"}}
        self.enhanced_slices = []

@pytest.fixture
def manager():
    analyzer = MockAnalyzer()
    return QuantityDisplayManager(analyzer)

def test_generate_quantity_list_display(manager):
    result = manager.generate_quantity_list_display()
    assert result["success"] is True
    assert len(result["components"]) == 1

def test_generate_ocr_recognition_display(manager):
    result = manager.generate_ocr_recognition_display()
    assert "drawing_basic_info" in result 