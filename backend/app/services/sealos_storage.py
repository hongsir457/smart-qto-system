#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sealos云存储服务
用于保存图像切片和分析结果
"""

import logging
import aiohttp
import asyncio
from typing import Optional, Dict, Any
from pathlib import Path
import hashlib
import json
from datetime import datetime

from app.core.config import settings

logger = logging.getLogger(__name__)

class SealosStorage:
    """Sealos云存储服务类"""
    
    def __init__(self):
        """初始化Sealos存储服务"""
        # 使用S3配置项，因为Sealos使用的是S3兼容存储
        # 使用S3配置项，因为Sealos使用的是S3兼容存储
        self.base_url = getattr(settings, 'S3_ENDPOINT', 'https://objectstorageapi.hzh.sealos.run')
        self.access_key = getattr(settings, 'S3_ACCESS_KEY', '')
        self.secret_key = getattr(settings, 'S3_SECRET_KEY', '')
        self.bucket_name = getattr(settings, 'S3_BUCKET_NAME', 'smart-qto-system')
        self.timeout = 30
        
        # 初始化本地存储路径
        self.local_storage_path = Path("storage/sealos_fallback")
        self.local_storage_path.mkdir(parents=True, exist_ok=True)
        
        # 检查配置完整性：需要endpoint、access_key、secret_key都不为空
        required_configs = [self.base_url, self.access_key, self.secret_key]
        self.use_local_fallback = not all(config.strip() for config in required_configs if config)
        
        if self.use_local_fallback:
            logger.warning(f"Sealos配置不完整，将使用本地存储作为备选")
            logger.debug(f"配置状态: endpoint={bool(self.base_url)}, access_key={bool(self.access_key)}, secret_key={bool(self.secret_key)}")
        else:
            logger.info(f"✅ Sealos存储服务初始化成功: {self.base_url}/{self.bucket_name}")
    
    async def upload_file(self, file_data: bytes, file_path: str, 
                         content_type: str = "application/octet-stream") -> str:
        """
        上传文件到Sealos存储
        
        Args:
            file_data: 文件数据
            file_path: 存储路径
            content_type: 内容类型
            
        Returns:
            文件访问URL
        """
        if self.use_local_fallback:
            return await self._upload_to_local(file_data, file_path)
        
        try:
            # 构建上传URL
            upload_url = f"{self.base_url}/api/v1/upload"
            
            # 生成文件哈希
            file_hash = hashlib.md5(file_data).hexdigest()
            
            # 准备请求头
            headers = {
                'Authorization': f'Bearer {self.access_key}',
                'Content-Type': content_type,
                'X-File-Hash': file_hash,
                'X-File-Path': file_path,
                'X-Bucket': self.bucket_name
            }
            
            # 上传文件
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.post(upload_url, data=file_data, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        file_url = result.get('url', f"{self.base_url}/{self.bucket_name}/{file_path}")
                        logger.info(f"文件上传成功: {file_path} -> {file_url}")
                        return file_url
                    else:
                        error_text = await response.text()
                        logger.error(f"文件上传失败: HTTP {response.status} - {error_text}")
                        # 失败时使用本地备选
                        return await self._upload_to_local(file_data, file_path)
                        
        except Exception as e:
            logger.error(f"Sealos上传异常: {e}")
            # 异常时使用本地备选
            return await self._upload_to_local(file_data, file_path)
    
    async def _upload_to_local(self, file_data: bytes, file_path: str) -> str:
        """
        本地存储备选方案
        
        Args:
            file_data: 文件数据
            file_path: 存储路径
            
        Returns:
            本地文件URL
        """
        try:
            # 创建本地文件路径（使用绝对路径）
            local_file_path = Path.cwd() / self.local_storage_path / file_path
            local_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入文件
            with open(local_file_path, 'wb') as f:
                f.write(file_data)
            
            # 生成访问URL（相对路径）
            try:
                relative_path = local_file_path.relative_to(Path.cwd())
                file_url = f"/{relative_path.as_posix()}"
            except ValueError:
                # 如果无法计算相对路径，使用绝对路径
                file_url = local_file_path.as_posix()
            
            logger.info(f"文件保存到本地: {file_path} -> {file_url}")
            return file_url
            
        except Exception as e:
            logger.error(f"本地存储失败: {e}")
            raise
    
    async def download_file(self, file_url: str) -> bytes:
        """
        从Sealos下载文件
        
        Args:
            file_url: 文件URL
            
        Returns:
            文件数据
        """
        if file_url.startswith('/'):
            # 本地文件
            return await self._download_from_local(file_url)
        
        try:
            headers = {
                'Authorization': f'Bearer {self.access_key}'
            }
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.get(file_url, headers=headers) as response:
                    if response.status == 200:
                        file_data = await response.read()
                        logger.info(f"文件下载成功: {file_url}")
                        return file_data
                    else:
                        error_text = await response.text()
                        logger.error(f"文件下载失败: HTTP {response.status} - {error_text}")
                        raise Exception(f"下载失败: {response.status}")
                        
        except Exception as e:
            logger.error(f"Sealos下载异常: {e}")
            raise
    
    async def _download_from_local(self, file_url: str) -> bytes:
        """
        从本地下载文件
        
        Args:
            file_url: 本地文件URL
            
        Returns:
            文件数据
        """
        try:
            # 转换为本地路径
            local_path = Path.cwd() / file_url.lstrip('/')
            
            if not local_path.exists():
                raise FileNotFoundError(f"本地文件不存在: {local_path}")
            
            with open(local_path, 'rb') as f:
                file_data = f.read()
            
            logger.info(f"本地文件读取成功: {file_url}")
            return file_data
            
        except Exception as e:
            logger.error(f"本地文件读取失败: {e}")
            raise
    
    async def delete_file(self, file_path: str) -> bool:
        """
        删除文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否删除成功
        """
        if self.use_local_fallback:
            return await self._delete_from_local(file_path)
        
        try:
            delete_url = f"{self.base_url}/api/v1/delete"
            
            headers = {
                'Authorization': f'Bearer {self.access_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'bucket': self.bucket_name,
                'file_path': file_path
            }
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.delete(delete_url, json=data, headers=headers) as response:
                    if response.status == 200:
                        logger.info(f"文件删除成功: {file_path}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"文件删除失败: HTTP {response.status} - {error_text}")
                        return False
                        
        except Exception as e:
            logger.error(f"Sealos删除异常: {e}")
            return False
    
    async def _delete_from_local(self, file_path: str) -> bool:
        """
        删除本地文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否删除成功
        """
        try:
            local_file_path = self.local_storage_path / file_path
            
            if local_file_path.exists():
                local_file_path.unlink()
                logger.info(f"本地文件删除成功: {file_path}")
                return True
            else:
                logger.warning(f"本地文件不存在: {file_path}")
                return True  # 文件不存在也算删除成功
                
        except Exception as e:
            logger.error(f"本地文件删除失败: {e}")
            return False
    
    async def list_files(self, prefix: str = "") -> list:
        """
        列出文件
        
        Args:
            prefix: 路径前缀
            
        Returns:
            文件列表
        """
        if self.use_local_fallback:
            return await self._list_local_files(prefix)
        
        try:
            list_url = f"{self.base_url}/api/v1/list"
            
            headers = {
                'Authorization': f'Bearer {self.access_key}'
            }
            
            params = {
                'bucket': self.bucket_name,
                'prefix': prefix
            }
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.get(list_url, params=params, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        files = result.get('files', [])
                        logger.info(f"文件列表获取成功: {len(files)} 个文件")
                        return files
                    else:
                        error_text = await response.text()
                        logger.error(f"文件列表获取失败: HTTP {response.status} - {error_text}")
                        return []
                        
        except Exception as e:
            logger.error(f"Sealos列表异常: {e}")
            return []
    
    async def _list_local_files(self, prefix: str = "") -> list:
        """
        列出本地文件
        
        Args:
            prefix: 路径前缀
            
        Returns:
            文件列表
        """
        try:
            search_path = self.local_storage_path
            if prefix:
                search_path = search_path / prefix
            
            files = []
            
            if search_path.exists():
                for file_path in search_path.rglob('*'):
                    if file_path.is_file():
                        relative_path = file_path.relative_to(self.local_storage_path)
                        files.append({
                            'name': file_path.name,
                            'path': relative_path.as_posix(),
                            'size': file_path.stat().st_size,
                            'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                        })
            
            logger.info(f"本地文件列表: {len(files)} 个文件")
            return files
            
        except Exception as e:
            logger.error(f"本地文件列表获取失败: {e}")
            return []
    
    async def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        获取文件信息
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件信息
        """
        if self.use_local_fallback:
            return await self._get_local_file_info(file_path)
        
        try:
            info_url = f"{self.base_url}/api/v1/info"
            
            headers = {
                'Authorization': f'Bearer {self.access_key}'
            }
            
            params = {
                'bucket': self.bucket_name,
                'file_path': file_path
            }
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.get(info_url, params=params, headers=headers) as response:
                    if response.status == 200:
                        file_info = await response.json()
                        logger.info(f"文件信息获取成功: {file_path}")
                        return file_info
                    else:
                        logger.error(f"文件信息获取失败: HTTP {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Sealos文件信息获取异常: {e}")
            return None
    
    async def _get_local_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        获取本地文件信息
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件信息
        """
        try:
            local_file_path = self.local_storage_path / file_path
            
            if not local_file_path.exists():
                return None
            
            stat = local_file_path.stat()
            
            file_info = {
                'name': local_file_path.name,
                'path': file_path,
                'size': stat.st_size,
                'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'type': 'file'
            }
            
            logger.info(f"本地文件信息获取成功: {file_path}")
            return file_info
            
        except Exception as e:
            logger.error(f"本地文件信息获取失败: {e}")
            return None 