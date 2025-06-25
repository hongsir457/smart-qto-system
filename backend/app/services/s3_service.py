#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S3云存储服务 - 支持本地存储fallback
"""

import boto3
import logging
import os
import uuid
import shutil
from typing import Optional, BinaryIO
from botocore.exceptions import ClientError, NoCredentialsError
from pathlib import Path
import aiofiles
import asyncio
from botocore.config import Config
from concurrent.futures import ThreadPoolExecutor

# S3配置通过延迟导入获取
logger = logging.getLogger(__name__)

class S3Service:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(S3Service, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # 只在第一次实例化时进行初始化
        if S3Service._initialized:
            return
            
        S3Service._initialized = True
        
        self.use_local_storage = False
        self.local_storage_path = Path("uploads")
        
        try:
            # 延迟导入配置以避免循环导入
            from ..core.config import settings
            
            self.endpoint_url = settings.S3_ENDPOINT
            self.access_key = settings.S3_ACCESS_KEY
            self.secret_key = settings.S3_SECRET_KEY
            self.bucket_name = settings.S3_BUCKET_NAME
            self.region = settings.S3_REGION
            self.use_local_storage = False  # 默认使用S3

            # 检查S3配置是否完整
            if not all([self.endpoint_url, self.access_key, self.secret_key, self.bucket_name]):
                logger.warning("S3配置不完整，将强制使用本地存储。")
                self.use_local_storage = True
                self._setup_local_storage()
                return
            
            # 初始化boto3客户端
            try:
                self.s3_client = boto3.client(
                    's3',
                    endpoint_url=self.endpoint_url,
                    aws_access_key_id=self.access_key,
                    aws_secret_access_key=self.secret_key,
                    region_name=self.region,
                    config=Config(signature_version='s3v4')
                )
                # logger.info("✅ S3客户端初始化成功。")
                
                # # 移除有害的连接测试，因为它可能因权限问题（而非连接问题）失败
                # # self.test_s3_connection()

            except Exception as e:
                logger.error(f"❌ S3客户端初始化失败: {e}，将切换到本地存储。")
                self.use_local_storage = True
            
            if self.use_local_storage:
                self._setup_local_storage()
            else:
                logger.info(f"✅ S3服务初始化成功，bucket: {self.bucket_name}")
                
            # 记录将要使用的S3配置
            logger.info(f"S3_ENDPOINT_URL: {self.endpoint_url}")
            logger.info(f"S3_ACCESS_KEY: {'*' * 5 if self.access_key else 'Not set'}")
            logger.info(f"S3_BUCKET_NAME (overridden): {self.bucket_name}")
            logger.info(f"S3_REGION: {self.region}")
                
        except Exception as e:
            logger.warning(f"⚠️ S3服务初始化失败: {str(e)}，使用本地存储")
            self.use_local_storage = True
            self._setup_local_storage()
    
    def _setup_local_storage(self):
        """设置本地存储"""
        self.use_local_storage = True
        self.local_storage_path.mkdir(exist_ok=True)
        (self.local_storage_path / "drawings").mkdir(exist_ok=True)
        logger.info(f"📁 本地存储已设置: {self.local_storage_path.absolute()}")
    
    def upload_file(
        self, 
        file_obj: BinaryIO, 
        file_name: str, 
        content_type: str = "application/octet-stream",
        folder: str = "drawings"
    ) -> dict:
        """
        上传文件到S3或本地存储
        """
        if self.use_local_storage:
            return self._upload_to_local(file_obj, file_name, folder)
        else:
            return self._upload_to_s3(file_obj, file_name, content_type, folder)
    
    def _upload_to_local(self, file_obj: BinaryIO, file_name: str, folder: str) -> dict:
        """上传文件到本地存储"""
        try:
            # 生成唯一的文件ID
            file_id = str(uuid.uuid4())
            file_ext = os.path.splitext(file_name)[1]
            local_filename = f"{file_id}{file_ext}"
            
            # 确保文件夹存在
            folder_path = self.local_storage_path / folder
            folder_path.mkdir(exist_ok=True)
            
            # 保存文件
            file_path = folder_path / local_filename
            with open(file_path, 'wb') as f:
                shutil.copyfileobj(file_obj, f)
            
            # 生成相对路径作为"s3_key"
            s3_key = f"{folder}/{local_filename}"
            file_url = f"file://{file_path.absolute()}"
            
            logger.info(f"✅ 文件已保存到本地: {file_path}")
            
            return {
                "s3_key": s3_key,
                "s3_url": file_url,
                "bucket": "local",
                "file_id": file_id,
                "original_filename": file_name,
                "local_path": str(file_path)
            }
            
        except Exception as e:
            logger.error(f"❌ 本地文件保存失败: {str(e)}")
            raise Exception(f"本地文件保存失败: {str(e)}")
    
    def _upload_to_s3(self, file_obj: BinaryIO, file_name: str, content_type: str, folder: str) -> dict:
        """上传文件到S3"""
        try:
            # 生成唯一的S3键名
            file_id = str(uuid.uuid4())
            file_ext = os.path.splitext(file_name)[1]
            s3_key = f"{folder}/{file_id}{file_ext}"
            
            logger.info(f"📤 开始上传文件到S3: {s3_key}")
            
            # 对中文文件名进行Base64编码以支持S3 metadata
            import base64
            encoded_filename = base64.b64encode(file_name.encode('utf-8')).decode('ascii')
            
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                s3_key,
                ExtraArgs={
                    'ContentType': content_type,
                    'Metadata': {
                        'original_filename_encoded': encoded_filename,
                        'uploaded_by': 'smart_qto_system',
                        'encoding': 'base64_utf8'
                    }
                }
            )
            
            # 生成S3文件URL
            file_url = f"{self.endpoint_url}/{self.bucket_name}/{s3_key}"
            
            logger.info(f"✅ 文件上传S3成功: {s3_key}")
            
            return {
                "s3_key": s3_key,
                "s3_url": file_url,
                "bucket": self.bucket_name,
                "file_id": file_id,
                "original_filename": file_name
            }
            
        except ClientError as e:
            logger.error(f"❌ S3上传失败: {str(e)}")
            raise Exception(f"S3上传失败: {str(e)}")
        except Exception as e:
            logger.error(f"❌ 文件上传异常: {str(e)}")
            raise
    
    def download_file(self, s3_key: str, local_path: str) -> bool:
        """
        从S3或本地存储下载文件
        """
        if self.use_local_storage:
            return self._download_from_local(s3_key, local_path)
        else:
            return self._download_from_s3(s3_key, local_path)
    
    def _download_from_local(self, s3_key: str, local_path: str) -> bool:
        """从本地存储"下载"文件（实际是复制）"""
        try:
            # s3_key格式：folder/filename
            source_path = self.local_storage_path / s3_key
            
            if not source_path.exists():
                logger.error(f"❌ 本地文件不存在: {source_path}")
                return False
            
            logger.info(f"📁 从本地复制文件: {source_path} → {local_path}")
            shutil.copy2(source_path, local_path)
            
            logger.info(f"✅ 文件复制成功: {local_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 本地文件复制失败: {str(e)}")
            return False
    
    def _download_from_s3(self, s3_key: str, local_path: str) -> bool:
        """从S3下载文件"""
        try:
            logger.info(f"📥 开始从S3下载文件: {s3_key} → {local_path}")
            
            self.s3_client.download_file(
                self.bucket_name,
                s3_key,
                local_path
            )
            
            logger.info(f"✅ 文件下载成功: {local_path}")
            return True
            
        except ClientError as e:
            logger.error(f"❌ S3下载失败: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"❌ 文件下载异常: {str(e)}")
            return False
    
    def delete_file(self, s3_key: str) -> bool:
        """
        删除S3或本地存储文件
        """
        if self.use_local_storage:
            return self._delete_from_local(s3_key)
        else:
            return self._delete_from_s3(s3_key)
    
    def _delete_from_local(self, s3_key: str) -> bool:
        """删除本地存储文件"""
        try:
            file_path = self.local_storage_path / s3_key
            
            if file_path.exists():
                file_path.unlink()
                logger.info(f"✅ 本地文件删除成功: {file_path}")
            else:
                logger.warning(f"⚠️ 本地文件不存在: {file_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 本地文件删除失败: {str(e)}")
            return False
    
    def _delete_from_s3(self, s3_key: str) -> bool:
        """删除S3文件"""
        try:
            logger.info(f"🗑️ 删除S3文件: {s3_key}")
            
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            logger.info(f"✅ S3文件删除成功: {s3_key}")
            return True
            
        except ClientError as e:
            logger.error(f"❌ S3删除失败: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"❌ 文件删除异常: {str(e)}")
            return False
    
    def decode_filename(self, encoded_filename: str) -> str:
        """
        解码Base64编码的文件名
        """
        try:
            import base64
            return base64.b64decode(encoded_filename.encode('ascii')).decode('utf-8')
        except Exception as e:
            logger.warning(f"文件名解码失败: {e}")
            return encoded_filename
    
    def get_file_info(self, s3_key: str) -> Optional[dict]:
        """
        获取文件信息
        """
        if self.use_local_storage:
            return self._get_local_file_info(s3_key)
        else:
            return self._get_s3_file_info(s3_key)
    
    def _get_local_file_info(self, s3_key: str) -> Optional[dict]:
        """获取本地文件信息"""
        try:
            file_path = self.local_storage_path / s3_key
            
            if not file_path.exists():
                return None
            
            stat = file_path.stat()
            return {
                "size": stat.st_size,
                "last_modified": stat.st_mtime,
                "content_type": "application/octet-stream",
                "metadata": {}
            }
            
        except Exception as e:
            logger.error(f"❌ 获取本地文件信息失败: {str(e)}")
            return None
    
    def _get_s3_file_info(self, s3_key: str) -> Optional[dict]:
        """获取S3文件信息"""
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            return {
                "size": response.get('ContentLength'),
                "last_modified": response.get('LastModified'),
                "content_type": response.get('ContentType'),
                "metadata": response.get('Metadata', {})
            }
            
        except ClientError as e:
            logger.error(f"❌ 获取S3文件信息失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"❌ 获取文件信息异常: {str(e)}")
            return None

    def generate_presigned_url(self, s3_key: str, expires_in: int = 3600) -> str:
        """生成指定文件的临时访问 URL，用于给大模型读取图片等资源。"""
        try:
            if self.use_local_storage:
                # 本地存储直接返回 file:// 路径
                local_path = self.local_storage_path / s3_key
                return f"file://{local_path.absolute()}"
            else:
                url = self.s3_client.generate_presigned_url(
                    ClientMethod="get_object",
                    Params={"Bucket": self.bucket_name, "Key": s3_key},
                    ExpiresIn=expires_in
                )
                return url
        except Exception as e:
            logger.error(f"❌ 生成 presigned URL 失败: {e}")
            raise

    def upload_content(self, content: str, s3_key: str, content_type: str = "application/json") -> bool:
        """上传字符串内容到S3或本地存储"""
        try:
            if self.use_local_storage:
                return self._upload_content_to_local(content, s3_key)
            else:
                return self._upload_content_to_s3(content, s3_key, content_type)
        except Exception as e:
            logger.error(f"上传内容失败: {e}")
            return False
    
    def _upload_content_to_local(self, content: str, s3_key: str) -> bool:
        """上传内容到本地存储"""
        try:
            file_path = self.local_storage_path / s3_key
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"✅ 内容已保存到本地: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 本地内容保存失败: {e}")
            return False
    
    def _upload_content_to_s3(self, content: str, s3_key: str, content_type: str) -> bool:
        """上传内容到S3"""
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=content.encode('utf-8'),
                ContentType=content_type
            )
            
            logger.info(f"✅ 内容上传S3成功: {s3_key}")
            return True
            
        except Exception as e:
            logger.error(f"❌ S3内容上传失败: {e}")
            return False
    
    def get_file_url(self, s3_key: str) -> str:
        """获取文件访问URL"""
        try:
            if self.use_local_storage:
                file_path = self.local_storage_path / s3_key
                return f"file://{file_path.absolute()}"
            else:
                return f"{self.endpoint_url}/{self.bucket_name}/{s3_key}"
        except Exception as e:
            logger.error(f"获取文件URL失败: {e}")
            return ""
    
    def upload_txt_content(self, content: str, file_name: str, folder: str = "ocr_results/txt") -> dict:
        """
        上传文本内容（TXT格式）到S3或本地存储
        
        Args:
            content: 文本内容
            file_name: 文件名
            folder: 存储文件夹路径
            
        Returns:
            包含上传结果信息的字典
        """
        if self.use_local_storage:
            return self._upload_txt_to_local(content, file_name, folder)
        else:
            return self._upload_txt_to_s3(content, file_name, folder)
    
    def _upload_txt_to_local(self, content: str, filename: str, folder: str) -> dict:
        """上传TXT到本地存储"""
        try:
            # 确保文件夹存在
            folder_path = self.local_storage_path / folder
            folder_path.mkdir(parents=True, exist_ok=True)
            
            # 保存文件
            file_path = folder_path / filename
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 生成相对路径作为"s3_key"
            s3_key = f"{folder}/{filename}"
            file_url = f"file://{file_path.absolute()}"
            
            logger.info(f"✅ TXT文件已保存到本地: {file_path}")
            
            return {
                "success": True,
                "s3_key": s3_key,
                "s3_url": file_url,
                "bucket": "local",
                "filename": filename,
                "local_path": str(file_path),
                "file_size": len(content.encode('utf-8'))
            }
            
        except Exception as e:
            logger.error(f"❌ 本地TXT文件保存失败: {str(e)}")
            raise Exception(f"本地TXT文件保存失败: {str(e)}")
    
    def _upload_txt_to_s3(self, content: str, filename: str, folder: str) -> dict:
        """上传TXT到S3"""
        try:
            s3_key = f"{folder}/{filename}"
            
            logger.info(f"📤 开始上传TXT文件到S3: {s3_key}")
            
            # 将内容编码为字节
            content_bytes = content.encode('utf-8')
            
            # 对中文文件名进行Base64编码
            import base64
            encoded_filename = base64.b64encode(filename.encode('utf-8')).decode('ascii')
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=content_bytes,
                ContentType='text/plain; charset=utf-8',
                Metadata={
                    'original_filename_encoded': encoded_filename,
                    'uploaded_by': 'smart_qto_system',
                    'encoding': 'utf8',
                    'content_type': 'paddleocr_txt_result'
                }
            )
            
            # 生成S3文件URL
            file_url = f"{self.endpoint_url}/{self.bucket_name}/{s3_key}"
            
            logger.info(f"✅ TXT文件上传S3成功: {s3_key}")
            
            return {
                "success": True,
                "s3_key": s3_key,
                "s3_url": file_url,
                "bucket": self.bucket_name,
                "filename": filename,
                "file_size": len(content_bytes)
            }
            
        except ClientError as e:
            logger.error(f"❌ S3 TXT上传失败: {str(e)}")
            raise Exception(f"S3 TXT上传失败: {str(e)}")
        except Exception as e:
            logger.error(f"❌ TXT文件上传异常: {str(e)}")
            raise

    async def download_content_async(self, s3_key: str) -> Optional[str]:
        """异步下载文件内容"""
        try:
            if self.use_local_storage:
                return await self._download_content_from_local_async(s3_key)
            else:
                return await self._download_content_from_s3_async(s3_key)
        except Exception as e:
            logger.error(f"❌ 异步下载内容失败 {s3_key}: {e}")
            return None

    def download_content_sync(self, s3_key: str) -> Optional[str]:
        """同步下载文件内容"""
        try:
            if self.use_local_storage:
                return self._download_content_from_local_sync(s3_key)
            else:
                return self._download_content_from_s3_sync(s3_key)
        except Exception as e:
            logger.error(f"❌ 同步下载内容失败 {s3_key}: {e}")
            return None

    async def _download_content_from_local_async(self, s3_key: str) -> Optional[str]:
        """从本地存储异步下载内容"""
        try:
            file_path = self.local_storage_path / s3_key
            
            if not file_path.exists():
                logger.warning(f"⚠️ 本地文件不存在: {file_path}")
                return None
            
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            logger.info(f"✅ 本地内容下载成功: {file_path}")
            return content
            
        except Exception as e:
            logger.error(f"❌ 本地异步下载失败: {e}")
            return None

    def _download_content_from_local_sync(self, s3_key: str) -> Optional[str]:
        """从本地存储同步下载内容"""
        try:
            file_path = self.local_storage_path / s3_key
            
            if not file_path.exists():
                logger.warning(f"⚠️ 本地文件不存在: {file_path}")
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            logger.info(f"✅ 本地内容下载成功: {file_path}")
            return content
            
        except Exception as e:
            logger.error(f"❌ 本地同步下载失败: {e}")
            return None

    async def _download_content_from_s3_async(self, s3_key: str) -> Optional[str]:
        """从S3异步下载内容"""
        try:
            # 在线程池中运行同步的S3操作
            def download_sync():
                response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
                content = response['Body'].read().decode('utf-8')
                return content
            
            content = await asyncio.get_event_loop().run_in_executor(None, download_sync)
            
            logger.info(f"✅ S3异步内容下载成功: {s3_key}")
            return content
            
        except Exception as e:
            logger.error(f"❌ S3异步下载失败: {e}")
            return None

    def _download_content_from_s3_sync(self, s3_key: str) -> Optional[str]:
        """从S3同步下载内容"""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            content = response['Body'].read().decode('utf-8')
            
            logger.info(f"✅ S3同步内容下载成功: {s3_key}")
            return content
            
        except ClientError as e:
            logger.error(f"❌ S3同步下载失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"❌ S3内容下载异常: {str(e)}")
            return None

    async def download_file_async(self, s3_key: str, local_path: str) -> bool:
        """异步下载文件到本地路径"""
        try:
            if self.use_local_storage:
                return await self._download_file_from_local_async(s3_key, local_path)
            else:
                return await self._download_file_from_s3_async(s3_key, local_path)
        except Exception as e:
            logger.error(f"❌ 异步下载文件失败 {s3_key}: {e}")
            return False

    def download_file_sync(self, s3_key: str, local_path: str) -> bool:
        """同步下载文件到本地路径"""
        return self.download_file(s3_key, local_path)

    async def _download_file_from_local_async(self, s3_key: str, local_path: str) -> bool:
        """从本地存储异步下载文件"""
        try:
            source_path = self.local_storage_path / s3_key
            
            if not source_path.exists():
                logger.warning(f"⚠️ 本地文件不存在: {source_path}")
                return False
            
            # 创建目标目录
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # 异步复制文件
            await asyncio.get_event_loop().run_in_executor(
                None, shutil.copy2, str(source_path), local_path
            )
            
            logger.info(f"✅ 本地文件下载成功: {local_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 本地异步文件下载失败: {e}")
            return False

    async def _download_file_from_s3_async(self, s3_key: str, local_path: str) -> bool:
        """从S3异步下载文件"""
        try:
            # 创建目标目录
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            await self.s3_client.download_file(self.bucket_name, s3_key, local_path)
            
            logger.info(f"✅ S3异步文件下载成功: {local_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ S3异步文件下载失败: {e}")
            return False

    def test_s3_connection(self):
        """
        测试与S3的连接。如果失败，则切换到本地存储。
        """
        # 此功能已禁用，因为它会导致权限问题
        pass
        # try:
        #     self.s3_client.head_bucket(Bucket=self.bucket_name)
        #     logger.info(f"✅ S3连接测试成功，可以使用Bucket: '{self.bucket_name}'")
        # except (ClientError, NoCredentialsError) as e:
        #     logger.warning(f"⚠️ S3连接测试失败: {e}，将切换到本地存储")
        #     self.use_local_storage = True

    def upload_file_sync(
        self, 
        file_obj: BinaryIO, 
        s3_key: str, 
        content_type: str = "application/octet-stream",
        original_filename: str = None
    ) -> dict:
        """
        【新】同步上传文件到S3或本地存储，使用完整的s3_key。
        
        Args:
            file_obj: 文件对象
            s3_key: 完整的S3键 (包括路径)
            content_type: 内容类型
            original_filename: 原始文件名，用于元数据
            
        Returns:
            上传结果
        """
        if self.use_local_storage:
            # 本地存储仍然需要拆分路径
            parts = s3_key.split('/')
            file_name_for_local = parts[-1]
            folder_for_local = '/'.join(parts[:-1]) if len(parts) > 1 else ""
            return self._upload_to_local(file_obj, file_name_for_local, folder_for_local)
        else:
            return self._upload_to_s3_sync(file_obj, s3_key, content_type, original_filename)

    def _upload_to_s3_sync(self, file_obj: BinaryIO, s3_key: str, content_type: str, original_filename: str = None) -> dict:
        """【新】使用完整的 s3_key 上传文件到S3"""
        try:
            # 如果没有提供原始文件名，从s3_key中提取
            if not original_filename:
                original_filename = os.path.basename(s3_key)

            logger.info(f"📤 开始上传文件到S3 (使用完整key): {s3_key}")
            
            # 对中文文件名进行Base64编码以支持S3 metadata
            import base64
            encoded_filename = base64.b64encode(original_filename.encode('utf-8')).decode('ascii')
            
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                s3_key, # 直接使用完整的s3_key
                ExtraArgs={
                    'ContentType': content_type,
                    'Metadata': {
                        'original_filename_encoded': encoded_filename,
                        'uploaded_by': 'smart_qto_system',
                        'encoding': 'base64_utf8'
                    }
                }
            )
            
            # 生成S3文件URL
            file_url = f"{self.endpoint_url}/{self.bucket_name}/{s3_key}"
            
            logger.info(f"✅ 文件上传S3成功 (使用完整key): {s3_key}")
            
            return {
                "s3_key": s3_key,
                "s3_url": file_url,
                "bucket": self.bucket_name,
                "file_id": os.path.basename(s3_key), # 使用文件名作为近似ID
                "original_filename": original_filename
            }
            
        except ClientError as e:
            logger.error(f"❌ S3上传失败 (使用完整key): {s3_key}, 错误: {str(e)}")
            raise Exception(f"S3上传失败: {str(e)}")
        except Exception as e:
            logger.error(f"❌ 文件上传异常 (使用完整key): {s3_key}, 错误: {str(e)}")
            raise

# 创建全局S3服务实例
s3_service = S3Service() 