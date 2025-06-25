import os
import uuid
from typing import Optional, Dict, Any
from pathlib import Path
import hashlib
import time

class FileNamingStrategy:
    """
    文件命名策略管理器
    统一管理文件上传、存储、下载的命名逻辑
    确保数据流一致性
    """
    
    # 支持的文件类型
    SUPPORTED_EXTENSIONS = {
        '.pdf': 'application/pdf',
        '.dwg': 'application/acad',
        '.dxf': 'application/dxf',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.tiff': 'image/tiff',
        '.tif': 'image/tiff'
    }
    
    # 文件夹映射
    FOLDER_MAP = {
        'drawings': 'drawings',
        'ocr_results': 'ocr_results',
        'temp': 'temp',
        'exports': 'exports'
    }
    
    @classmethod
    def generate_storage_key(cls, original_filename: str, folder: str = "drawings", 
                           file_id: Optional[str] = None) -> Dict[str, Any]:
        """
        生成存储键名和相关信息
        
        Args:
            original_filename: 原始文件名
            folder: 文件夹名称 (drawings, ocr_results, exports等)
            file_id: 可选的文件ID，如果不提供则生成UUID
            
        Returns:
            Dict包含: s3_key, local_filename, folder, file_extension, content_type
        """
        # 提取文件扩展名
        file_ext = Path(original_filename).suffix.lower()
        
        # 验证文件类型
        if file_ext not in cls.SUPPORTED_EXTENSIONS:
            raise ValueError(f"不支持的文件类型: {file_ext}")
        
        # 生成文件ID（如果未提供）
        if not file_id:
            file_id = str(uuid.uuid4())
        
        # 生成存储文件名（使用UUID避免文件名冲突和编码问题）
        storage_filename = f"{file_id}{file_ext}"
        
        # 获取标准化的文件夹名
        folder = cls.FOLDER_MAP.get(folder, folder)
        
        # 生成S3键名（相对路径）
        s3_key = f"{folder}/{storage_filename}"
        
        return {
            "s3_key": s3_key,
            "storage_filename": storage_filename,
            "original_filename": original_filename,
            "folder": folder,
            "file_extension": file_ext,
            "content_type": cls.SUPPORTED_EXTENSIONS[file_ext],
            "file_id": file_id
        }
    
    @classmethod
    def generate_export_filename(cls, base_name: str, export_type: str, 
                                timestamp: Optional[str] = None) -> str:
        """
        生成导出文件名
        
        Args:
            base_name: 基础名称（通常是原始文件名）
            export_type: 导出类型 (excel, json, pdf等)
            timestamp: 可选时间戳
            
        Returns:
            格式化的导出文件名
        """
        # 清理基础名称
        safe_base = cls._sanitize_filename(base_name)
        
        # 添加时间戳（如果未提供）
        if not timestamp:
            timestamp = str(int(time.time()))
        
        # 导出类型到扩展名的映射
        ext_map = {
            'excel': '.xlsx',
            'json': '.json',
            'pdf': '.pdf'
        }
        
        extension = ext_map.get(export_type, f'.{export_type}')
        
        return f"{safe_base}_{export_type}_{timestamp}{extension}"
    
    @classmethod
    def _sanitize_filename(cls, filename: str) -> str:
        """
        清理文件名，移除不安全字符
        
        Args:
            filename: 原始文件名
            
        Returns:
            清理后的安全文件名
        """
        # 移除文件扩展名
        base_name = Path(filename).stem
        
        # 替换不安全字符
        unsafe_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', ' ']
        safe_name = base_name
        for char in unsafe_chars:
            safe_name = safe_name.replace(char, '_')
        
        # 限制长度
        if len(safe_name) > 100:
            safe_name = safe_name[:100]
        
        return safe_name
    
    @classmethod
    def parse_s3_key(cls, s3_key: str) -> Dict[str, str]:
        """
        解析S3键名，提取文件夹和文件名信息
        
        Args:
            s3_key: S3键名，格式如 "drawings/uuid.pdf"
            
        Returns:
            Dict包含: folder, filename, file_id, extension
        """
        path_parts = s3_key.split('/')
        if len(path_parts) != 2:
            raise ValueError(f"Invalid S3 key format: {s3_key}")
        
        folder, filename = path_parts
        file_path = Path(filename)
        file_id = file_path.stem
        extension = file_path.suffix
        
        return {
            "folder": folder,
            "filename": filename,
            "file_id": file_id,
            "extension": extension
        }
    
    @classmethod
    def validate_file_type(cls, filename: str) -> bool:
        """
        验证文件类型是否支持
        
        Args:
            filename: 文件名
            
        Returns:
            是否支持该文件类型
        """
        file_ext = Path(filename).suffix.lower()
        return file_ext in cls.SUPPORTED_EXTENSIONS
    
    @classmethod
    def get_content_type(cls, filename: str) -> str:
        """
        根据文件名获取MIME类型
        
        Args:
            filename: 文件名
            
        Returns:
            MIME类型字符串
        """
        file_ext = Path(filename).suffix.lower()
        return cls.SUPPORTED_EXTENSIONS.get(file_ext, 'application/octet-stream')


class FileLifecycleManager:
    """
    文件生命周期管理器
    处理文件的创建、更新、删除等操作
    确保文件在所有存储位置的一致性
    """
    
    def __init__(self, s3_service=None, db_session=None):
        self.s3_service = s3_service
        self.db_session = db_session
    
    async def create_file_record(self, file_info: Dict[str, Any], user_id: int, 
                               additional_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        创建文件记录（数据库+存储）
        
        Args:
            file_info: 文件信息
            user_id: 用户ID
            additional_data: 额外的文件数据
            
        Returns:
            创建结果
        """
        # 这里可以添加创建逻辑
        # 当前版本先返回基本结构
        return {
            "success": True,
            "file_info": file_info,
            "user_id": user_id
        }
    
    async def delete_file_completely(self, drawing_id: int, user_id: int) -> Dict[str, Any]:
        """
        完全删除文件（数据库记录 + S3存储 + 本地临时文件）
        
        Args:
            drawing_id: 图纸ID
            user_id: 用户ID
            
        Returns:
            删除结果
        """
        from ..models.drawing import Drawing
        
        if not self.db_session:
            raise ValueError("Database session not provided")
        
        # 查找文件记录
        drawing = self.db_session.query(Drawing).filter(
            Drawing.id == drawing_id,
            Drawing.user_id == user_id
        ).first()
        
        if not drawing:
            return {"success": False, "message": "文件不存在或无权限"}
        
        results = {
            "drawing_id": drawing_id,
            "filename": drawing.filename,
            "s3_deleted": False,
            "local_deleted": False,
            "db_deleted": False,
            "errors": []
        }
        
        # 1. 删除S3文件
        if drawing.s3_key and self.s3_service:
            try:
                if self.s3_service.delete_file(drawing.s3_key):
                    results["s3_deleted"] = True
                else:
                    results["errors"].append("S3文件删除失败")
            except Exception as e:
                results["errors"].append(f"S3删除异常: {str(e)}")
        
        # 2. 删除本地文件（如果存在）
        if drawing.file_path and os.path.exists(drawing.file_path):
            try:
                os.unlink(drawing.file_path)
                results["local_deleted"] = True
            except Exception as e:
                results["errors"].append(f"本地文件删除失败: {str(e)}")
        
        # 3. 删除数据库记录
        try:
            self.db_session.delete(drawing)
            self.db_session.commit()
            results["db_deleted"] = True
        except Exception as e:
            results["errors"].append(f"数据库删除失败: {str(e)}")
            self.db_session.rollback()
        
        results["success"] = results["db_deleted"]  # 以数据库删除为主要成功标准
        
        return results


# 全局实例
file_naming_strategy = FileNamingStrategy() 