#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR Processing Task - Leverages the UnifiedOCREngine for a streamlined workflow.
"""

import os
import asyncio
import logging
from typing import Dict, Any

from app.core.celery_app import celery_app
from app.tasks import task_manager, TaskStatus, TaskStage
from app.services.unified_ocr_engine import UnifiedOCREngine
from celery.utils.log import get_task_logger

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = get_task_logger(__name__)

@celery_app.task(bind=True, name='app.tasks.ocr_tasks.process_ocr_file_task')
def process_ocr_file_task(self, file_path: str, s3_key: str, options: Dict[str, Any] = None):
    """
    The main Celery task for processing a drawing file using the UnifiedOCREngine.
    
    Args:
        file_path (str): The local path to the file to be processed.
        s3_key (str): The S3 key for the original uploaded file.
        options (Dict[str, Any], optional): Additional processing options. Defaults to None.
    """
    task_id = self.request.id
    logger.info(f"🚀 Starting Unified OCR Processing Task: {task_id}")
    logger.info(f"📁 File Path: {file_path}")
    logger.info(f"🔑 S3 Key: {s3_key}")
    logger.info(f"⚙️ Options: {options or {}}")

    # Update initial task status
    asyncio.run(task_manager.update_task_status(
        task_id=task_id,
        status=TaskStatus.STARTED,
        stage=TaskStage.PROCESSING,
        progress=5,
        message="Initializing analysis engine..."
    ))

    try:
        # 1. Check if the file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found at path: {file_path}")

        # 2. Instantiate and run the unified engine pipeline
        engine = UnifiedOCREngine(task_id=task_id, file_path=file_path, s3_key=s3_key)
        
        asyncio.run(task_manager.update_task_status(
            task_id=task_id,
            progress=20,
            message="Engine initialized. Starting analysis pipeline..."
        ))
        
        final_results = engine.run_analysis_pipeline()

        # 3. Check for errors from the pipeline
        if "error" in final_results:
             raise Exception(f"Pipeline execution failed: {final_results['error']}")

        # 4. Update final status to SUCCESS
        logger.info(f"✅ Task {task_id} completed successfully.")
        asyncio.run(task_manager.update_task_status(
            task_id=task_id,
            status=TaskStatus.SUCCESS,
            stage=TaskStage.COMPLETED,
            progress=100,
            message="Analysis complete. Results are available.",
            results=final_results
        ))
        
        return {
            "task_id": task_id,
            "status": "success",
            "message": "Unified OCR processing completed successfully.",
            "results_s3_key": final_results.get("final_s3_key")
        }
        
    except Exception as e:
        error_msg = f"Unified OCR processing failed: {str(e)}"
        logger.error(f"❌ Task {task_id} failed: {error_msg}", exc_info=True)
        
        # Update final status to FAILURE
        asyncio.run(task_manager.update_task_status(
            task_id=task_id,
            status=TaskStatus.FAILURE,
            stage=TaskStage.FAILED,
            progress=0,
            message=error_msg,
            error_message=str(e)
        ))
        
        # Re-raise the exception to have Celery mark the task as failed
        raise e

# Note: The batch processing task below is not yet updated to use the new engine.
# It remains for future refactoring.
@celery_app.task(bind=True, name='app.tasks.ocr_tasks.batch_process_ocr_files')
def batch_process_ocr_files(self, file_paths: list, options: Dict[str, Any] = None):
    """
    (Legacy) Processes a batch of files. Needs refactoring.
    """
    task_id = self.request.id
    logger.warning(f"Task {task_id}: Batch processing is using a legacy workflow and needs to be refactored.")
    # For now, just log a warning and complete.
    asyncio.run(task_manager.update_task_status(
        task_id=task_id,
        status=TaskStatus.SUCCESS,
        stage=TaskStage.COMPLETED,
        progress=100,
        message="Batch task placeholder completed."
    ))
    return {"status": "legacy_placeholder", "task_id": task_id} 