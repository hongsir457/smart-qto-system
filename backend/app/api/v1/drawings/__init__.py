"""
图纸相关API模块

将原本的大型drawings.py文件拆分为以下子模块：
- upload.py: 文件上传相关API
- list.py: 图纸列表和详情API
- process.py: OCR和构件检测API
- status.py: 任务状态查询API
- export.py: 导出相关API
- delete.py: 删除操作API
"""

from fastapi import APIRouter
from . import upload, list, process, status, export, delete

# 创建主路由器
router = APIRouter()

# 注册各个子模块的路由，添加适当的前缀避免冲突
router.include_router(upload.router, prefix="", tags=["图纸上传"])
router.include_router(list.router, prefix="", tags=["图纸列表"])
router.include_router(process.router, prefix="", tags=["图纸处理"])
router.include_router(status.router, prefix="", tags=["任务状态"])
router.include_router(export.router, prefix="", tags=["结果导出"])
router.include_router(delete.router, prefix="", tags=["图纸删除"]) 