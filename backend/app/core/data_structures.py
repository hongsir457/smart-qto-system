"""
智能工程量分析系统 - 核心数据结构设计
统一中间格式定义，确保各处理步骤间的数据一致性
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union, Tuple
from enum import Enum
from datetime import datetime
import json


# ================================
# 1. 基础枚举类型定义
# ================================

class ComponentType(Enum):
    """构件类型枚举"""
    COLUMN = "column"           # 柱
    BEAM = "beam"              # 梁
    WALL = "wall"              # 墙
    SLAB = "slab"              # 板
    FOUNDATION = "foundation"   # 基础
    STAIR = "stair"            # 楼梯
    DOOR = "door"              # 门
    WINDOW = "window"          # 窗
    OTHER = "other"            # 其他

class ProcessingStage(Enum):
    """处理阶段枚举"""
    PREPROCESSING = "preprocessing"     # Step1: 预处理
    OCR_RECOGNITION = "ocr_recognition" # Step2: OCR识别
    OCR_CLEANING = "ocr_cleaning"       # Step2.5: OCR清洗
    GLOBAL_OVERVIEW = "global_overview" # Step3: 全图概览
    VISION_ANALYSIS = "vision_analysis" # Step4: Vision分析
    RESULT_FUSION = "result_fusion"     # Step5: 结果融合
    COORDINATE_RESTORATION = "coordinate_restoration" # Step6: 坐标还原

class ConfidenceLevel(Enum):
    """置信度等级"""
    HIGH = "high"       # 高置信度 (>0.8)
    MEDIUM = "medium"   # 中等置信度 (0.5-0.8)
    LOW = "low"         # 低置信度 (<0.5)

class DataSource(Enum):
    """数据来源"""
    OCR = "ocr"                    # OCR识别
    VISION = "vision"              # Vision分析
    FUSION = "fusion"              # 融合结果
    MANUAL = "manual"              # 人工标注


# ================================
# 2. 几何与空间数据结构
# ================================

@dataclass
class Point2D:
    """二维坐标点"""
    x: float
    y: float
    
    def to_dict(self) -> Dict:
        return {"x": self.x, "y": self.y}

@dataclass
class BoundingBox:
    """边界框"""
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    confidence: float = 1.0
    
    @property
    def width(self) -> float:
        return self.x_max - self.x_min
    
    @property
    def height(self) -> float:
        return self.y_max - self.y_min
    
    @property
    def center(self) -> Point2D:
        return Point2D(
            x=(self.x_min + self.x_max) / 2,
            y=(self.y_min + self.y_max) / 2
        )
    
    def to_dict(self) -> Dict:
        return {
            "x_min": self.x_min,
            "y_min": self.y_min,
            "x_max": self.x_max,
            "y_max": self.y_max,
            "width": self.width,
            "height": self.height,
            "center": self.center.to_dict(),
            "confidence": self.confidence
        }

@dataclass
class Dimensions:
    """构件尺寸信息"""
    length: Optional[float] = None      # 长度(m)
    width: Optional[float] = None       # 宽度(m)
    height: Optional[float] = None      # 高度(m)
    thickness: Optional[float] = None   # 厚度(m)
    diameter: Optional[float] = None    # 直径(m)
    area: Optional[float] = None        # 面积(m²)
    volume: Optional[float] = None      # 体积(m³)
    
    def to_dict(self) -> Dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


# ================================
# 3. 文本与识别数据结构
# ================================

@dataclass
class OCRTextResult:
    """OCR文本识别结果"""
    text: str                           # 识别文本
    bbox: BoundingBox                   # 文本边界框
    confidence: float                   # 识别置信度
    slice_id: str                       # 所属切片ID
    text_type: str = "unknown"          # 文本类型(dimension/label/material等)
    
    def to_dict(self) -> Dict:
        return {
            "text": self.text,
            "bbox": self.bbox.to_dict(),
            "confidence": self.confidence,
            "slice_id": self.slice_id,
            "text_type": self.text_type
        }

@dataclass
class SliceInfo:
    """图纸切片信息"""
    slice_id: str                       # 切片唯一ID
    bbox: BoundingBox                   # 切片在原图中的位置
    image_path: str                     # 切片图像路径
    priority: int = 1                   # 处理优先级
    content_density: float = 0.0        # 内容密度
    
    def to_dict(self) -> Dict:
        return {
            "slice_id": self.slice_id,
            "bbox": self.bbox.to_dict(),
            "image_path": self.image_path,
            "priority": self.priority,
            "content_density": self.content_density
        }


# ================================
# 4. 构件核心数据结构
# ================================

@dataclass
class ComponentCore:
    """构件核心信息（统一格式）"""
    # 基本标识
    component_id: str                   # 构件唯一ID
    component_type: ComponentType       # 构件类型
    label: str = ""                     # 构件标签/编号
    
    # 几何信息
    bbox: Optional[BoundingBox] = None  # 边界框
    dimensions: Optional[Dimensions] = None # 尺寸信息
    
    # 属性信息
    material: str = ""                  # 材料类型
    grade: str = ""                     # 强度等级
    specification: str = ""             # 规格描述
    
    # 位置信息
    floor_level: str = ""               # 楼层
    axis_line: str = ""                 # 轴线
    grid_position: str = ""             # 网格位置
    
    # 数据质量
    confidence: float = 0.0             # 整体置信度
    confidence_level: ConfidenceLevel = ConfidenceLevel.LOW
    data_source: DataSource = DataSource.OCR
    
    # 处理信息
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    processing_stage: ProcessingStage = ProcessingStage.OCR_RECOGNITION
    
    # 原始数据引用
    source_texts: List[OCRTextResult] = field(default_factory=list)
    source_slices: List[str] = field(default_factory=list)
    
    def update_confidence_level(self):
        """根据置信度更新等级"""
        if self.confidence > 0.8:
            self.confidence_level = ConfidenceLevel.HIGH
        elif self.confidence > 0.5:
            self.confidence_level = ConfidenceLevel.MEDIUM
        else:
            self.confidence_level = ConfidenceLevel.LOW
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        self.update_confidence_level()
        return {
            "component_id": self.component_id,
            "component_type": self.component_type.value,
            "label": self.label,
            "bbox": self.bbox.to_dict() if self.bbox else None,
            "dimensions": self.dimensions.to_dict() if self.dimensions else {},
            "material": self.material,
            "grade": self.grade,
            "specification": self.specification,
            "floor_level": self.floor_level,
            "axis_line": self.axis_line,
            "grid_position": self.grid_position,
            "confidence": self.confidence,
            "confidence_level": self.confidence_level.value,
            "data_source": self.data_source.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "processing_stage": self.processing_stage.value,
            "source_texts": [text.to_dict() for text in self.source_texts],
            "source_slices": self.source_slices
        }


# ================================
# 5. 处理阶段数据结构
# ================================

@dataclass
class PreprocessingResult:
    """Step1: 预处理结果"""
    drawing_id: str
    original_image_path: str
    slices: List[SliceInfo]
    frame_detected: bool = False
    frame_bbox: Optional[BoundingBox] = None
    total_slices: int = 0
    processing_time: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "drawing_id": self.drawing_id,
            "original_image_path": self.original_image_path,
            "slices": [slice_info.to_dict() for slice_info in self.slices],
            "frame_detected": self.frame_detected,
            "frame_bbox": self.frame_bbox.to_dict() if self.frame_bbox else None,
            "total_slices": len(self.slices),
            "processing_time": self.processing_time
        }

@dataclass
class OCRResult:
    """Step2: OCR识别结果"""
    drawing_id: str
    slice_results: Dict[str, List[OCRTextResult]]  # slice_id -> OCR结果列表
    total_texts: int = 0
    avg_confidence: float = 0.0
    processing_time: float = 0.0
    
    def calculate_stats(self):
        """计算统计信息"""
        all_texts = []
        for texts in self.slice_results.values():
            all_texts.extend(texts)
        
        self.total_texts = len(all_texts)
        if all_texts:
            self.avg_confidence = sum(text.confidence for text in all_texts) / len(all_texts)
    
    def to_dict(self) -> Dict:
        self.calculate_stats()
        return {
            "drawing_id": self.drawing_id,
            "slice_results": {
                slice_id: [text.to_dict() for text in texts]
                for slice_id, texts in self.slice_results.items()
            },
            "total_texts": self.total_texts,
            "avg_confidence": self.avg_confidence,
            "processing_time": self.processing_time
        }

@dataclass
class OCRCleaningResult:
    """Step2.5: OCR清洗结果"""
    drawing_id: str
    cleaned_components: List[ComponentCore]
    drawing_info: Dict[str, Any] = field(default_factory=dict)
    component_overview: Dict[str, Any] = field(default_factory=dict)
    quality_metrics: Dict[str, float] = field(default_factory=dict)
    processing_time: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "drawing_id": self.drawing_id,
            "cleaned_components": [comp.to_dict() for comp in self.cleaned_components],
            "drawing_info": self.drawing_info,
            "component_overview": self.component_overview,
            "quality_metrics": self.quality_metrics,
            "processing_time": self.processing_time
        }

@dataclass
class VisionAnalysisResult:
    """Step4: Vision分析结果"""
    drawing_id: str
    vision_components: List[ComponentCore]
    spatial_relationships: Dict[str, Any] = field(default_factory=dict)
    enhanced_attributes: Dict[str, Dict] = field(default_factory=dict)
    processing_time: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "drawing_id": self.drawing_id,
            "vision_components": [comp.to_dict() for comp in self.vision_components],
            "spatial_relationships": self.spatial_relationships,
            "enhanced_attributes": self.enhanced_attributes,
            "processing_time": self.processing_time
        }

@dataclass
class FusionResult:
    """Step5: 融合结果"""
    drawing_id: str
    fused_components: List[ComponentCore]
    fusion_report: Dict[str, Any] = field(default_factory=dict)
    conflict_resolutions: List[Dict] = field(default_factory=list)
    quality_score: float = 0.0
    processing_time: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "drawing_id": self.drawing_id,
            "fused_components": [comp.to_dict() for comp in self.fused_components],
            "fusion_report": self.fusion_report,
            "conflict_resolutions": self.conflict_resolutions,
            "quality_score": self.quality_score,
            "processing_time": self.processing_time
        }


# ================================
# 6. 工程量计算数据结构
# ================================

@dataclass
class QuantityItem:
    """工程量清单项"""
    item_id: str                        # 清单项ID
    component_id: str                   # 关联构件ID
    component_type: ComponentType       # 构件类型
    specification: str                  # 规格描述
    unit: str                          # 计量单位
    quantity: float                    # 工程量
    unit_price: float = 0.0            # 单价
    total_price: float = 0.0           # 合价
    confidence: float = 1.0            # 计算置信度
    calculation_rule: str = ""         # 计算规则
    
    def calculate_total(self):
        """计算合价"""
        self.total_price = self.quantity * self.unit_price
    
    def to_dict(self) -> Dict:
        self.calculate_total()
        return {
            "item_id": self.item_id,
            "component_id": self.component_id,
            "component_type": self.component_type.value,
            "specification": self.specification,
            "unit": self.unit,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "total_price": self.total_price,
            "confidence": self.confidence,
            "calculation_rule": self.calculation_rule
        }

@dataclass
class QuantityList:
    """工程量清单"""
    drawing_id: str
    project_info: Dict[str, str] = field(default_factory=dict)
    quantity_items: List[QuantityItem] = field(default_factory=list)
    summary_by_type: Dict[str, Dict] = field(default_factory=dict)
    total_summary: Dict[str, Any] = field(default_factory=dict)
    compliance_check: Dict[str, bool] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.now)
    
    def calculate_summary(self):
        """计算汇总信息"""
        type_stats = {}
        total_quantity = 0.0
        total_value = 0.0
        
        for item in self.quantity_items:
            comp_type = item.component_type.value
            if comp_type not in type_stats:
                type_stats[comp_type] = {
                    "count": 0,
                    "total_quantity": 0.0,
                    "total_value": 0.0
                }
            
            type_stats[comp_type]["count"] += 1
            type_stats[comp_type]["total_quantity"] += item.quantity
            type_stats[comp_type]["total_value"] += item.total_price
            
            total_quantity += item.quantity
            total_value += item.total_price
        
        self.summary_by_type = type_stats
        self.total_summary = {
            "total_items": len(self.quantity_items),
            "total_quantity": total_quantity,
            "total_value": total_value,
            "component_types": list(type_stats.keys())
        }
    
    def to_dict(self) -> Dict:
        self.calculate_summary()
        return {
            "drawing_id": self.drawing_id,
            "project_info": self.project_info,
            "quantity_items": [item.to_dict() for item in self.quantity_items],
            "summary_by_type": self.summary_by_type,
            "total_summary": self.total_summary,
            "compliance_check": self.compliance_check,
            "generated_at": self.generated_at.isoformat()
        }


# ================================
# 7. 完整分析结果数据结构
# ================================

@dataclass
class AnalysisResult:
    """完整分析结果（所有步骤的统一输出）"""
    drawing_id: str
    task_id: str
    
    # 各步骤结果
    preprocessing: Optional[PreprocessingResult] = None
    ocr_result: Optional[OCRResult] = None
    ocr_cleaning: Optional[OCRCleaningResult] = None
    vision_analysis: Optional[VisionAnalysisResult] = None
    fusion_result: Optional[FusionResult] = None
    quantity_list: Optional[QuantityList] = None
    
    # 全局状态
    status: str = "processing"
    progress: float = 0.0
    error_message: str = ""
    
    # 时间信息
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    total_processing_time: float = 0.0
    
    # 质量评估
    overall_quality: float = 0.0
    quality_breakdown: Dict[str, float] = field(default_factory=dict)
    
    def calculate_overall_quality(self):
        """计算整体质量分数"""
        scores = []
        
        if self.ocr_cleaning and self.ocr_cleaning.quality_metrics:
            scores.append(self.ocr_cleaning.quality_metrics.get("overall_quality", 0.0))
        
        if self.fusion_result:
            scores.append(self.fusion_result.quality_score)
        
        if self.quantity_list and self.quantity_list.compliance_check:
            compliance_rate = sum(self.quantity_list.compliance_check.values()) / len(self.quantity_list.compliance_check)
            scores.append(compliance_rate)
        
        self.overall_quality = sum(scores) / len(scores) if scores else 0.0
    
    def to_dict(self) -> Dict:
        """转换为完整字典格式"""
        self.calculate_overall_quality()
        
        return {
            "drawing_id": self.drawing_id,
            "task_id": self.task_id,
            "status": self.status,
            "progress": self.progress,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_processing_time": self.total_processing_time,
            "overall_quality": self.overall_quality,
            "quality_breakdown": self.quality_breakdown,
            "preprocessing": self.preprocessing.to_dict() if self.preprocessing else None,
            "ocr_result": self.ocr_result.to_dict() if self.ocr_result else None,
            "ocr_cleaning": self.ocr_cleaning.to_dict() if self.ocr_cleaning else None,
            "vision_analysis": self.vision_analysis.to_dict() if self.vision_analysis else None,
            "fusion_result": self.fusion_result.to_dict() if self.fusion_result else None,
            "quantity_list": self.quantity_list.to_dict() if self.quantity_list else None
        }


# ================================
# 8. 数据转换工具函数
# ================================

class DataConverter:
    """数据格式转换工具"""
    
    @staticmethod
    def from_dict(data: Dict, target_class) -> Any:
        """从字典创建数据结构对象"""
        # 这里可以实现通用的字典到数据类的转换逻辑
        pass
    
    @staticmethod
    def to_json(obj: Any) -> str:
        """转换为JSON字符串"""
        if hasattr(obj, 'to_dict'):
            return json.dumps(obj.to_dict(), ensure_ascii=False, indent=2)
        return json.dumps(obj, ensure_ascii=False, indent=2)
    
    @staticmethod
    def from_json(json_str: str, target_class) -> Any:
        """从JSON字符串创建对象"""
        data = json.loads(json_str)
        return DataConverter.from_dict(data, target_class)


# ================================
# 9. 数据验证工具
# ================================

class DataValidator:
    """数据验证工具"""
    
    @staticmethod
    def validate_component(component: ComponentCore) -> List[str]:
        """验证构件数据完整性"""
        errors = []
        
        if not component.component_id:
            errors.append("构件ID不能为空")
        
        if not component.component_type:
            errors.append("构件类型不能为空")
        
        if component.confidence < 0 or component.confidence > 1:
            errors.append("置信度必须在0-1之间")
        
        return errors
    
    @staticmethod
    def validate_quantity_list(quantity_list: QuantityList) -> List[str]:
        """验证工程量清单"""
        errors = []
        
        if not quantity_list.drawing_id:
            errors.append("图纸ID不能为空")
        
        if not quantity_list.quantity_items:
            errors.append("工程量清单不能为空")
        
        for item in quantity_list.quantity_items:
            if item.quantity <= 0:
                errors.append(f"工程量必须大于0: {item.item_id}")
        
        return errors


if __name__ == "__main__":
    # 示例用法
    print("智能工程量分析系统 - 核心数据结构")
    print("=" * 50)
    
    # 创建示例构件
    component = ComponentCore(
        component_id="C001",
        component_type=ComponentType.COLUMN,
        label="C1",
        dimensions=Dimensions(length=0.4, width=0.4, height=3.0, volume=0.48),
        material="C30混凝土",
        confidence=0.85
    )
    
    print("示例构件数据:")
    print(json.dumps(component.to_dict(), ensure_ascii=False, indent=2)) 