# ChatGPT智能工程量分析API接口
import os
import tempfile
import uuid
from typing import Dict, Any, Optional
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.services.chatgpt_quantity_analyzer import ChatGPTQuantityAnalyzer
from app.models.drawing import Drawing
from app.database import SafeDBSession
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class ProjectContext(BaseModel):
    """项目背景信息"""
    project_name: str = Field(None, description="项目名称")
    building_type: str = Field(None, description="建筑类型")
    structure_type: str = Field("框架结构", description="结构类型")
    design_stage: str = Field("施工图设计", description="设计阶段")
    special_requirements: str = Field(None, description="特殊要求")

class ChatGPTAnalysisRequest(BaseModel):
    """ChatGPT分析请求"""
    api_key: str = Field(..., description="OpenAI API密钥")
    api_base: str = Field("https://api.openai.com/v1", description="API基础URL")
    project_context: Optional[ProjectContext] = None

class AnalysisResult(BaseModel):
    """分析结果响应"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="分析状态")
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    excel_download_url: Optional[str] = None

# 存储分析任务结果的内存字典（生产环境应使用Redis等）
analysis_tasks = {}

@router.post("/analyze-pdf", response_model=AnalysisResult)
async def analyze_drawing_pdf(
    background_tasks: BackgroundTasks,
    pdf_file: UploadFile = File(..., description="施工图PDF文件"),
    request_data: str = None,  # JSON字符串形式的ChatGPTAnalysisRequest
    current_user: Any = Depends(get_current_user)
):
    """
    分析施工图PDF并生成工程量清单
    
    使用ChatGPT-4V智能识别构件并计算工程量
    """
    try:
        # 解析请求参数
        if request_data:
            import json
            request_dict = json.loads(request_data)
            analysis_request = ChatGPTAnalysisRequest(**request_dict)
        else:
            # 使用默认配置（需要环境变量中有API密钥）
            analysis_request = ChatGPTAnalysisRequest(
                api_key=os.getenv('OPENAI_API_KEY'),
                api_base=os.getenv('OPENAI_API_BASE', 'https://api.openai.com/v1')
            )
        
        if not analysis_request.api_key:
            raise HTTPException(
                status_code=400,
                detail="必须提供OpenAI API密钥，可通过环境变量OPENAI_API_KEY或请求参数提供"
            )
        
        # 检查文件类型
        if not pdf_file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="只支持PDF文件")
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 初始化任务状态
        analysis_tasks[task_id] = {
            "status": "processing",
            "result": None,
            "error_message": None,
            "excel_path": None
        }
        
        # 在后台执行分析任务
        background_tasks.add_task(
            process_pdf_analysis,
            task_id,
            pdf_file,
            analysis_request,
            current_user
        )
        
        return AnalysisResult(
            task_id=task_id,
            status="processing"
        )
        
    except Exception as e:
        logger.error(f"启动PDF分析任务时发生错误: {e}")
        raise HTTPException(status_code=500, detail=f"分析启动失败: {str(e)}")

@router.get("/analysis-status/{task_id}", response_model=AnalysisResult)
async def get_analysis_status(
    task_id: str,
    current_user: Any = Depends(get_current_user)
):
    """
    查询分析任务状态
    """
    if task_id not in analysis_tasks:
        raise HTTPException(status_code=404, detail="任务ID不存在")
    
    task_data = analysis_tasks[task_id]
    
    result = AnalysisResult(
        task_id=task_id,
        status=task_data["status"],
        result=task_data.get("result"),
        error_message=task_data.get("error_message")
    )
    
    # 如果有Excel文件，提供下载链接
    if task_data.get("excel_path") and os.path.exists(task_data["excel_path"]):
        result.excel_download_url = f"/api/v1/chatgpt-analysis/download-excel/{task_id}"
    
    return result

@router.get("/download-excel/{task_id}")
async def download_excel(
    task_id: str,
    current_user: Any = Depends(get_current_user)
):
    """
    下载分析结果Excel文件
    """
    if task_id not in analysis_tasks:
        raise HTTPException(status_code=404, detail="任务ID不存在")
    
    task_data = analysis_tasks[task_id]
    excel_path = task_data.get("excel_path")
    
    if not excel_path or not os.path.exists(excel_path):
        raise HTTPException(status_code=404, detail="Excel文件不存在")
    
    return FileResponse(
        path=excel_path,
        filename=f"工程量清单_{task_id[:8]}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@router.delete("/analysis/{task_id}")
async def delete_analysis_task(
    task_id: str,
    current_user: Any = Depends(get_current_user)
):
    """
    删除分析任务和相关文件
    """
    if task_id not in analysis_tasks:
        raise HTTPException(status_code=404, detail="任务ID不存在")
    
    task_data = analysis_tasks[task_id]
    
    # 删除Excel文件
    excel_path = task_data.get("excel_path")
    if excel_path and os.path.exists(excel_path):
        try:
            os.remove(excel_path)
            logger.info(f"已删除Excel文件: {excel_path}")
        except Exception as e:
            logger.warning(f"删除Excel文件失败: {e}")
    
    # 删除任务记录
    del analysis_tasks[task_id]
    
    return {"message": f"任务 {task_id} 已删除"}

@router.get("/supported-models")
async def get_supported_models():
    """
    获取支持的ChatGPT模型列表
    """
    return {
        "models": [
            {
                "id": "chatgpt-4o-latest",
                "name": "ChatGPT-4o Latest",
                "description": "最新的ChatGPT-4o模型，支持图像分析和高质量文本生成",
                "recommended": True
            },
            {
                "id": "gpt-4o-2024-11-20",
                "name": "GPT-4o (2024-11-20)",
                "description": "GPT-4o模型的特定版本，支持图像分析",
                "recommended": True
            }
        ]
    }

async def process_pdf_analysis(
    task_id: str,
    pdf_file: UploadFile,
    analysis_request: ChatGPTAnalysisRequest,
    current_user: Any
):
    """
    后台处理PDF分析任务
    """
    try:
        logger.info(f"开始处理分析任务: {task_id}")
        
        # 创建临时文件保存上传的PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            content = await pdf_file.read()
            tmp_file.write(content)
            tmp_pdf_path = tmp_file.name
        
        try:
            # 初始化ChatGPT分析器
            analyzer = ChatGPTQuantityAnalyzer(
                api_key=analysis_request.api_key,
                api_base=analysis_request.api_base
            )
            
            # 准备项目上下文
            project_context = None
            if analysis_request.project_context:
                project_context = analysis_request.project_context.dict()
            
            # 执行分析
            logger.info(f"开始ChatGPT分析: {pdf_file.filename}")
            analysis_result = analyzer.analyze_drawing_pdf(tmp_pdf_path, project_context)
            
            if "error" in analysis_result:
                # 分析失败
                analysis_tasks[task_id]["status"] = "failed"
                analysis_tasks[task_id]["error_message"] = analysis_result["error"]
                logger.error(f"分析失败: {analysis_result['error']}")
                return
            
            # 生成Excel文件
            excel_dir = Path("temp/analysis_results")
            excel_dir.mkdir(parents=True, exist_ok=True)
            excel_path = excel_dir / f"工程量清单_{task_id}.xlsx"
            
            success = analyzer.export_to_excel(analysis_result, str(excel_path))
            if not success:
                logger.warning("Excel导出失败，但分析结果仍然可用")
            
            # 保存到数据库（可选）
            try:
                with SafeDBSession() as session:
                    drawing_record = Drawing(
                        filename=pdf_file.filename,
                        file_path=tmp_pdf_path,
                        analysis_result=analysis_result,
                        analysis_method="chatgpt",
                        user_id=getattr(current_user, 'id', None)
                    )
                    session.add(drawing_record)
                    session.commit()
                    logger.info(f"分析结果已保存到数据库")
            except Exception as e:
                logger.warning(f"保存到数据库失败: {e}")
            
            # 更新任务状态
            analysis_tasks[task_id]["status"] = "completed"
            analysis_tasks[task_id]["result"] = analysis_result
            if success:
                analysis_tasks[task_id]["excel_path"] = str(excel_path)
            
            logger.info(f"分析任务完成: {task_id}, 识别到 {len(analysis_result.get('quantity_list', []))} 个工程量项目")
            
        finally:
            # 清理临时PDF文件
            try:
                os.remove(tmp_pdf_path)
            except Exception as e:
                logger.warning(f"删除临时PDF文件失败: {e}")
                
    except Exception as e:
        logger.error(f"处理分析任务 {task_id} 时发生错误: {e}")
        analysis_tasks[task_id]["status"] = "failed"
        analysis_tasks[task_id]["error_message"] = str(e)

# 清理过期任务的定时任务（可以用celery等替代）
@router.on_event("startup")
async def setup_cleanup_task():
    """设置清理任务"""
    import asyncio
    
    async def cleanup_expired_tasks():
        while True:
            try:
                # 每小时清理一次超过24小时的任务
                current_time = time.time()
                expired_tasks = []
                
                for task_id, task_data in analysis_tasks.items():
                    task_age = current_time - task_data.get("created_at", current_time)
                    if task_age > 24 * 3600:  # 24小时
                        expired_tasks.append(task_id)
                
                for task_id in expired_tasks:
                    try:
                        task_data = analysis_tasks[task_id]
                        excel_path = task_data.get("excel_path")
                        if excel_path and os.path.exists(excel_path):
                            os.remove(excel_path)
                        del analysis_tasks[task_id]
                        logger.info(f"清理过期任务: {task_id}")
                    except Exception as e:
                        logger.warning(f"清理任务 {task_id} 失败: {e}")
                
                await asyncio.sleep(3600)  # 1小时
                
            except Exception as e:
                logger.error(f"清理任务时发生错误: {e}")
                await asyncio.sleep(3600)
    
    # 在后台启动清理任务
    import time
    for task_data in analysis_tasks.values():
        task_data["created_at"] = time.time()
    
    asyncio.create_task(cleanup_expired_tasks()) 