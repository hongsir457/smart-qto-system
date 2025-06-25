import asyncio
import json
import logging
from typing import Dict, Any, Optional, Union
from io import BytesIO
from pathlib import Path
import requests
import os

from .s3_service import S3Service
from .sealos_storage import SealosStorage

logger = logging.getLogger(__name__)

class DualStorageService:
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(DualStorageService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if DualStorageService._initialized:
            return
        DualStorageService._initialized = True
        self.s3_service = None
        self.sealos_service = None
        self.active_service = None
        
        try:
            self._initialize_services()
            logger.info("双重存储服务初始化完成")
        except Exception as e:
            logger.error(f"双重存储服务初始化失败: {e}")

    def is_available(self) -> bool:
        """只要有一个主用存储可用就返回True，并输出调试日志"""
        logger = logging.getLogger(__name__)
        available = self.active_service is not None
        logger.info(f"[DualStorageService][is_available] called: active_service={type(self.active_service).__name__ if self.active_service else None}, result={available}")
        return available

    def _initialize_services(self):
        """初始化双重存储服务，优先使用S3"""
        logger = logging.getLogger(__name__)
        self.s3_service = S3Service()
        self.sealos_storage = SealosStorage()

        # 检查S3配置完整性
        s3_config_complete = all([
            self.s3_service.endpoint_url,
            self.s3_service.access_key,
            self.s3_service.secret_key,
            self.s3_service.bucket_name
        ])

        logger.info(f"[DualStorageService][_initialize_services] S3配置完整: {s3_config_complete}")
        logger.info(f"[DualStorageService][_initialize_services] S3 endpoint: {self.s3_service.endpoint_url}, bucket: {self.s3_service.bucket_name}")
        logger.info(f"[DualStorageService][_initialize_services] Sealos endpoint: {getattr(self.sealos_storage, 'endpoint_url', None)}")

        # 优先S3
        if s3_config_complete:
            try:
                logger.info("✅ S3配置完整，将S3作为主存储。")
                self.primary_storage = self.s3_service
                self.active_service = self.s3_service
                self.fallback_storage = self.sealos_storage
                logger.info(f"[DualStorageService][_initialize_services] active_service set to S3Service")
            except Exception as e:
                logger.warning(f"⚠️ S3初始化异常: {e}")
                self.primary_storage = None
        else:
            logger.warning("⚠️ S3配置不完整，将Sealos存储作为主存储。")
            self.primary_storage = self.sealos_storage
            self.active_service = self.sealos_storage
            self.fallback_storage = None
            logger.info(f"[DualStorageService][_initialize_services] active_service set to SealosStorage")

        # 如果S3和Sealos都不可用，active_service为None
        if not self.active_service:
            logger.error("❌ 没有可用的主用存储，active_service=None")

        # 本地存储路径
        self.local_storage_path = Path("storage/dual_storage_fallback")
        self.local_storage_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"[DualStorageService][_initialize_services] 本地存储路径: {self.local_storage_path}")
        
    def upload_file_sync(self, file_obj: Union[BytesIO, bytes], 
                        s3_key: str,
                        content_type: str = "application/octet-stream") -> Dict[str, Any]:
        """
        同步文件上传（三层存储策略）
        
        Args:
            file_obj: 文件对象或字节数据
            s3_key: 完整的S3存储键 (包含文件夹路径)
            content_type: 内容类型
            
        Returns:
            上传结果信息
        """
        storage_results = {
            "success": False,
            "primary_storage": None,
            "backup_storage": None,
            "final_url": None,
            "storage_method": None,
            "error": None
        }
        
        try:
            # 第一层：S3Service主存储
            try:
                if isinstance(file_obj, bytes):
                    file_obj = BytesIO(file_obj)
                
                s3_result = self.s3_service.upload_file_sync(
                    file_obj=file_obj,
                    s3_key=s3_key,
                    content_type=content_type
                )
                
                storage_results["primary_storage"] = s3_result
                storage_results["final_url"] = s3_result.get("s3_url")
                storage_results["storage_method"] = "s3_primary"
                storage_results["success"] = True
                
                logger.info(f"✅ S3主存储上传成功: {s3_key}")
                return storage_results
                
            except Exception as e:
                logger.warning(f"⚠️ S3主存储上传失败: {e}")
                storage_results["error"] = f"S3主存储失败: {e}"
            
            # 第二层：本地存储降级
            try:
                # 为了本地降级，需要从s3_key解析文件名和文件夹
                parts = s3_key.split('/')
                file_name = parts[-1]
                folder = '/'.join(parts[:-1]) if len(parts) > 1 else ""

                local_result = self._upload_to_local_sync(file_obj, file_name, folder)
                storage_results["backup_storage"] = local_result
                storage_results["final_url"] = local_result.get("local_url")
                storage_results["storage_method"] = "local_fallback"
                storage_results["success"] = True
                
                logger.info(f"✅ 本地存储降级成功: {s3_key}")
                return storage_results
                
            except Exception as e:
                logger.error(f"❌ 本地存储也失败: {e}")
                storage_results["error"] += f"; 本地存储失败: {e}"
            
            # 所有存储都失败
            storage_results["success"] = False
            raise Exception(f"所有存储方式都失败: {storage_results['error']}")
            
        except Exception as e:
            logger.error(f"❌ 双重存储上传完全失败: {e}")
            storage_results["error"] = str(e)
            return storage_results

    async def upload_file_async(self, file_data: bytes, 
                              file_path: str,
                              content_type: str = "application/octet-stream") -> str:
        """
        异步文件上传（三层存储策略）
        
        Args:
            file_data: 文件数据
            file_path: 存储路径
            content_type: 内容类型
            
        Returns:
            文件访问URL
        """
        try:
            # 第一层：S3Service主存储
            try:
                # 🔧 修复：将bytes转换为BytesIO对象
                from io import BytesIO
                file_obj = BytesIO(file_data)
                
                # S3Service的upload_file方法期望文件对象，需要分解路径
                import os
                folder, file_name = os.path.dirname(file_path), os.path.basename(file_path)
                if not folder:
                    folder = "drawings"  # 默认文件夹
                
                result = self.s3_service.upload_file(file_obj, file_name, content_type, folder)
                url = result.get("s3_url", "")
                logger.info(f"✅ S3异步存储上传成功: {file_path}")
                return url
            except Exception as e:
                logger.warning(f"⚠️ S3异步存储上传失败: {e}")
            
            # 第二层：Sealos备份存储
            try:
                if hasattr(self, 'sealos_storage') and self.sealos_storage:
                    url = await self.sealos_storage.upload_file(file_data, file_path, content_type)
                    logger.info(f"✅ Sealos备份存储上传成功: {file_path}")
                    return url
                else:
                    logger.debug("Sealos存储服务不可用，跳过")
            except Exception as e:
                logger.warning(f"⚠️ Sealos备份存储上传失败: {e}")
            
            # 第三层：本地存储降级
            try:
                url = await self._upload_to_local_async(file_data, file_path)
                logger.info(f"✅ 本地异步存储降级成功: {file_path}")
                return url
            except Exception as e:
                logger.error(f"❌ 本地异步存储也失败: {e}")
            
            raise Exception("所有异步存储方式都失败")
            
        except Exception as e:
            logger.error(f"❌ 异步双重存储上传失败: {e}")
            raise

    def upload_content_sync(self, content: str, 
                          s3_key: str,
                          content_type: str = "application/json") -> Dict[str, Any]:
        """
        同步内容上传
        
        Args:
            content: 文本内容
            s3_key: 存储键
            content_type: 内容类型
            
        Returns:
            上传结果信息
        """
        try:
            # 转换为字节数据
            content_bytes = content.encode('utf-8')
            file_obj = BytesIO(content_bytes)
            
            # 修改：直接调用，不再拆分 s3_key
            return self.upload_file_sync(
                file_obj=file_obj,
                s3_key=s3_key,
                content_type=content_type
            )
            
        except Exception as e:
            logger.error(f"同步内容上传失败: {e}")
            raise

    async def upload_content_async(self, content: str, 
                                 key: str,
                                 content_type: str = "application/json") -> str:
        """
        异步内容上传
        
        Args:
            content: 文本内容
            key: 存储键
            content_type: 内容类型
            
        Returns:
            文件访问URL
        """
        try:
            content_bytes = content.encode('utf-8')
            return await self.upload_file_async(content_bytes, key, content_type)
        except Exception as e:
            logger.error(f"异步内容上传失败: {e}")
            raise

    def _upload_to_local_sync(self, file_obj: Union[BytesIO, bytes], 
                            file_name: str, 
                            folder: str) -> Dict[str, Any]:
        """同步本地存储"""
        try:
            # 创建目录
            local_folder = self.local_storage_path / folder
            local_folder.mkdir(parents=True, exist_ok=True)
            
            # 保存文件
            file_path = local_folder / file_name
            
            if isinstance(file_obj, BytesIO):
                file_obj.seek(0)
                with open(file_path, 'wb') as f:
                    f.write(file_obj.read())
            elif isinstance(file_obj, bytes):
                with open(file_path, 'wb') as f:
                    f.write(file_obj)
            else:
                raise ValueError("不支持的文件对象类型")
            
            return {
                "local_path": str(file_path),
                "local_url": f"file://{file_path.absolute()}",
                "size": file_path.stat().st_size
            }
            
        except Exception as e:
            logger.error(f"本地同步存储失败: {e}")
            raise

    async def _upload_to_local_async(self, file_data: bytes, file_path: str) -> str:
        """异步本地存储"""
        try:
            # 创建完整路径
            full_path = self.local_storage_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 异步写入文件
            def write_file():
                with open(full_path, 'wb') as f:
                    f.write(file_data)
            
            # 在线程池中执行文件写入
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, write_file)
            
            return f"file://{full_path.absolute()}"
            
        except Exception as e:
            logger.error(f"本地异步存储失败: {e}")
            raise

    def upload_txt_content(self, content: str, 
                         file_name: str, 
                         folder: str = "txt_content") -> Dict[str, Any]:
        """
        上传TXT文本内容（同步）
        
        Args:
            content: 文本内容
            file_name: 文件名（不含扩展名）
            folder: 存储文件夹
            
        Returns:
            上传结果信息
        """
        try:
            # 确保文件名有.txt扩展名
            if not file_name.endswith('.txt'):
                file_name += '.txt'
            
            return self.upload_content_sync(
                content=content,
                s3_key=f"{folder}/{file_name}",
                content_type="text/plain"
            )
            
        except Exception as e:
            logger.error(f"TXT内容上传失败: {e}")
            raise

    async def upload_json_content_async(self, data: Dict[str, Any], 
                                      file_path: str) -> str:
        """
        异步上传JSON内容
        
        Args:
            data: 要序列化的数据
            file_path: 存储路径
            
        Returns:
            文件访问URL
        """
        try:
            json_content = json.dumps(data, ensure_ascii=False, indent=2)
            return await self.upload_content_async(
                content=json_content,
                key=file_path,
                content_type="application/json"
            )
        except Exception as e:
            logger.error(f"JSON内容异步上传失败: {e}")
            raise

    def get_storage_status(self) -> Dict[str, Any]:
        """获取存储服务状态"""
        status = {
            "s3_service_available": False,
            "s3_storage_available": False,
            "sealos_storage_available": False,
            "local_storage_available": False,
            "local_storage_path": str(self.local_storage_path)
        }
        
        try:
            # 检查S3Service
            if hasattr(self.s3_service, 's3_client'):
                status["s3_service_available"] = True
        except:
            pass
        
        try:
            # 检查本地存储
            if self.local_storage_path.exists():
                status["local_storage_available"] = True
        except:
            pass
        
        # 其他存储服务需要异步检查
        status["note"] = "S3Storage和SealosStorage状态需要异步检查"
        
        return status

    def cleanup_local_storage(self, days_old: int = 7) -> Dict[str, Any]:
        """
        清理本地存储中的旧文件
        
        Args:
            days_old: 清理多少天前的文件
            
        Returns:
            清理结果统计
        """
        import time
        from datetime import datetime, timedelta
        
        cleanup_stats = {
            "files_checked": 0,
            "files_deleted": 0,
            "space_freed_mb": 0,
            "errors": []
        }
        
        try:
            cutoff_time = time.time() - (days_old * 24 * 60 * 60)
            
            for file_path in self.local_storage_path.rglob("*"):
                if file_path.is_file():
                    cleanup_stats["files_checked"] += 1
                    
                    try:
                        if file_path.stat().st_mtime < cutoff_time:
                            file_size = file_path.stat().st_size
                            file_path.unlink()
                            cleanup_stats["files_deleted"] += 1
                            cleanup_stats["space_freed_mb"] += file_size / (1024 * 1024)
                    except Exception as e:
                        cleanup_stats["errors"].append(f"删除文件失败 {file_path}: {e}")
            
            logger.info(f"本地存储清理完成: 删除了 {cleanup_stats['files_deleted']} 个文件, "
                       f"释放了 {cleanup_stats['space_freed_mb']:.2f} MB空间")
            
        except Exception as e:
            logger.error(f"本地存储清理失败: {e}")
            cleanup_stats["errors"].append(str(e))
        
        return cleanup_stats

    def download_file(self, s3_key: str, local_path: str) -> bool:
        """
        双重存储文件下载（同步）
        尝试从S3、Sealos、本地存储依次下载
        
        Args:
            s3_key: S3存储键或URL
            local_path: 本地保存路径
            
        Returns:
            是否下载成功
        """
        try:
            logger.info(f"🔄 开始双重存储下载: {s3_key} → {local_path}")
            
            # 方法1: 尝试从S3下载
            try:
                logger.info("📥 尝试从S3存储下载...")
                # 从URL中提取S3 key
                actual_s3_key = s3_key
                if s3_key.startswith('http'):
                    from urllib.parse import urlparse
                    parsed_url = urlparse(s3_key)
                    # 从URL路径中提取S3 key（去掉bucket名称）
                    path_parts = parsed_url.path.strip('/').split('/')
                    if len(path_parts) >= 2:
                        # 跳过bucket名称，取后面的路径作为s3_key
                        actual_s3_key = '/'.join(path_parts[1:])
                    else:
                        actual_s3_key = path_parts[-1] if path_parts else s3_key
                    logger.info(f"📥 开始从S3下载文件: {s3_key} → {local_path}")
                    logger.info(f"📥 提取的S3 Key: {actual_s3_key}")
                
                if self.s3_service.download_file(actual_s3_key, local_path):
                    logger.info("✅ S3下载成功")
                    return True
                else:
                    logger.warning("⚠️ S3下载失败，尝试备用方案")
            except Exception as e:
                logger.error(f"❌ S3下载失败: {e}")
                logger.warning("⚠️ S3下载失败，尝试备用方案")

            # 方法2: 尝试从Sealos存储下载（如果URL包含sealos域名）
            if "sealos.run" in s3_key or "sealos.io" in s3_key:
                try:
                    logger.info("📥 尝试从Sealos存储下载...")
                    
                    # 使用requests进行同步HTTP下载
                    headers = {
                        'Authorization': f'Bearer {self.sealos_storage.access_key}'
                    }
                    
                    logger.info(f"📥 Sealos同步下载: {s3_key}")
                    response = requests.get(s3_key, headers=headers, timeout=30)
                    
                    if response.status_code == 200:
                        # 保存文件到本地路径
                        with open(local_path, 'wb') as f:
                            f.write(response.content)
                        logger.info("✅ Sealos下载成功")
                        return True
                    else:
                        logger.warning(f"⚠️ Sealos下载失败: HTTP {response.status_code}")
                        
                except Exception as e:
                    logger.warning(f"⚠️ Sealos下载异常: {e}")

            # 方法3: 尝试从本地存储下载
            try:
                logger.info("📥 尝试从本地存储下载...")
                # 从s3_key中提取相对路径
                if s3_key.startswith('http'):
                    # 如果是URL，提取文件名
                    from urllib.parse import urlparse
                    parsed_url = urlparse(s3_key)
                    path_parts = parsed_url.path.strip('/').split('/')
                    relative_path = '/'.join(path_parts[1:]) if len(path_parts) > 1 else path_parts[-1]
                else:
                    relative_path = s3_key
                
                # 确保使用正确的路径分隔符
                local_stored_path = self.local_storage_path / relative_path
                
                logger.info(f"📥 检查本地存储路径: {local_stored_path}")
                
                if local_stored_path.exists():
                    # 复制文件到目标位置
                    import shutil
                    shutil.copy2(local_stored_path, local_path)
                    logger.info(f"✅ 本地存储下载成功: {local_stored_path}")
                    return True
                else:
                    logger.warning(f"⚠️ 本地存储中未找到文件: {local_stored_path}")
            except Exception as e:
                logger.warning(f"⚠️ 本地存储下载异常: {e}")

            # 如果所有方法都失败
            logger.error(f"❌ 双重存储下载失败: 所有存储方式都无法下载文件 {s3_key}")
            return False
            
        except Exception as e:
            logger.error(f"❌ 双重存储下载异常: {e}")
            return False

    async def download_file_async(self, file_key: str, local_path: str) -> bool:
        """异步下载文件到本地路径"""
        try:
            if self.s3_service:
                success = await self.s3_service.download_file_async(file_key, local_path)
                if success:
                    return True
            
            # 尝试HTTP下载
            if hasattr(self, '_try_http_download'):
                return await self._try_http_download(file_key, local_path)
                
            return False
        except Exception as e:
            logger.error(f"❌ 异步下载文件失败 {file_key}: {e}")
            return False

    async def download_content_async(self, file_key: str) -> Optional[Dict[str, Any]]:
        """异步下载文件内容并解析为JSON"""
        try:
            # 方法1: 使用S3直接下载内容
            if self.s3_service and hasattr(self.s3_service, 'download_content_async'):
                content = await self.s3_service.download_content_async(file_key)
                if content:
                    return json.loads(content) if isinstance(content, str) else content
            
            # 方法2: 使用临时文件下载
            import tempfile
            import aiofiles
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as temp_file:
                temp_path = temp_file.name
            
            try:
                # 下载到临时文件
                download_success = await self.download_file_async(file_key, temp_path)
                if download_success:
                    # 读取临时文件内容
                    async with aiofiles.open(temp_path, 'r', encoding='utf-8') as f:
                        content = await f.read()
                        return json.loads(content)
            finally:
                # 清理临时文件
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            
            # 方法3: 尝试HTTP下载内容
            if hasattr(self, '_try_http_download_content'):
                return await self._try_http_download_content(file_key)
                
            return None
            
        except Exception as e:
            logger.error(f"❌ 异步下载内容失败 {file_key}: {e}")
            return None

    def download_content_sync(self, file_key: str) -> Optional[Dict[str, Any]]:
        """同步下载文件内容并解析为JSON"""
        try:
            # 方法1: 使用S3直接下载内容
            if self.s3_service and hasattr(self.s3_service, 'download_content_sync'):
                content = self.s3_service.download_content_sync(file_key)
                if content:
                    return json.loads(content) if isinstance(content, str) else content
            
            # 方法2: 使用临时文件下载
            import tempfile
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as temp_file:
                temp_path = temp_file.name
            
            try:
                # 下载到临时文件
                download_success = self.download_file_sync(file_key, temp_path)
                if download_success:
                    # 读取临时文件内容
                    with open(temp_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        return json.loads(content)
            finally:
                # 清理临时文件
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ 同步下载内容失败 {file_key}: {e}")
            return None

    def download_file_sync(self, file_key: str, local_path: str) -> bool:
        """同步下载文件到本地路径"""
        try:
            if self.s3_service:
                success = self.s3_service.download_file_sync(file_key, local_path)
                if success:
                    return True
            
            # 尝试HTTP下载
            if hasattr(self, '_try_http_download_sync'):
                return self._try_http_download_sync(file_key, local_path)
                
            return False
        except Exception as e:
            logger.error(f"❌ 同步下载文件失败 {file_key}: {e}")
            return False