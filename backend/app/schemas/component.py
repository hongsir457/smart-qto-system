from pydantic import BaseModel, Field
from typing import List, Tuple, Dict, Any, Optional

class ComponentPosition(BaseModel):
    slice_id: str = Field(..., description="来源切片的唯一标识")
    bbox_local: Tuple[float, float, float, float] = Field(..., description="在切片内的局部坐标 [x1, y1, x2, y2]")
    bbox_global: Tuple[float, float, float, float] = Field(..., description="在原图纸中的全局坐标 [X1, Y1, X2, Y2]")

class ComponentGeometry(BaseModel):
    length_mm: Optional[float] = Field(None, description="长度（毫米）")
    width_mm: Optional[float] = Field(None, description="宽度（毫米）")
    height_mm: Optional[float] = Field(None, description="高度（毫米）")
    # 可以添加更多几何属性，如面积、体积等
    area_sqm: Optional[float] = Field(None, description="面积（平方米）")
    volume_cbm: Optional[float] = Field(None, description="体积（立方米）")

class ComponentConfidence(BaseModel):
    ocr_confidence: Optional[float] = Field(None, description="OCR识别的置信度")
    vision_confidence: Optional[float] = Field(None, description="Vision模型识别的置信度")
    fusion_confidence: float = Field(..., description="融合后的最终置信度")

class DrawingComponent(BaseModel):
    id: str = Field(..., description="构件的唯一标识，例如 'beam_1023' 或从构件编号生成")
    component_type: str = Field(..., description="构件类型，例如 '梁', '柱', '板'")
    component_id: Optional[str] = Field(None, description="图纸上标注的构件编号，如 'L1', 'KZ2'")
    
    position: ComponentPosition = Field(..., description="构件的位置信息")
    
    text_tags: List[str] = Field(default_factory=list, description="通过OCR关联到的文本标签，如配筋信息、型号、说明等")
    
    geometry: Optional[ComponentGeometry] = Field(None, description="构件的几何尺寸信息")
    
    source_modules: List[str] = Field(..., description="识别来源模块，例如 ['OCR', 'Vision']")
    
    confidence: ComponentConfidence = Field(..., description="置信度评分")
    
    floor: Optional[str] = Field(None, description="构件所属楼层")
    drawing_name: Optional[str] = Field(None, description="来源图纸名称")
    
    # 内部处理字段
    raw_ocr_texts: List[Dict[str, Any]] = Field(default_factory=list, description="关联到的原始OCR文本区域，用于调试和追溯")
    raw_vision_data: Optional[Dict[str, Any]] = Field(None, description="Vision模型返回的原始数据，用于调试")

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": "beam_1023",
                "component_type": "梁",
                "component_id": "L-3",
                "position": {
                    "slice_id": "slice_3",
                    "bbox_local": (100.5, 200.0, 350.5, 250.0),
                    "bbox_global": (1100.5, 1200.0, 1350.5, 1250.0)
                },
                "text_tags": ["KL-3(2A)", "500x250", "N8@100/200(2)"],
                "geometry": {
                    "length_mm": 6000,
                    "width_mm": 250,
                    "height_mm": 500
                },
                "source_modules": ["Vision", "OCR"],
                "confidence": {
                    "vision_confidence": 0.85,
                    "ocr_confidence": 0.92,
                    "fusion_confidence": 0.91
                },
                "floor": "三层",
                "drawing_name": "结构施工图_3.dwg"
            }
        } 