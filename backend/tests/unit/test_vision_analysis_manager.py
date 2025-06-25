import pytest
from app.services.vision_analysis_manager import VisionAnalysisManager

class MockAnalyzer:
    def __init__(self):
        self.ai_analyzer = None
        self.enhanced_slices = []
        self.slice_components = {}
        self.global_drawing_overview = {}
        self._vision_cache = {}

@pytest.fixture
def manager():
    analyzer = MockAnalyzer()
    return VisionAnalysisManager(analyzer)

def test_generate_basic_vision_prompt(manager):
    class SliceInfo:
        row = 1
        col = 2
    drawing_info = {"scale": "1:100", "drawing_number": "A01"}
    prompt = manager.generate_basic_vision_prompt(SliceInfo(), drawing_info)
    assert "结构图切片" in prompt

def test_parse_vision_components_empty(manager):
    class SliceInfo:
        filename = "test.png"
    result = manager.parse_vision_components({"components": []}, SliceInfo())
    assert result == [] 