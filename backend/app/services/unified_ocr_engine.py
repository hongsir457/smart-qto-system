#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified OCR Engine - The sole entry point for architectural drawing analysis.
This engine orchestrates the entire pipeline from document processing to AI analysis.
"""
import json
import logging
import os
import tempfile
import time
from typing import Dict, List, Any, Optional
import fitz  # PyMuPDF
from PIL import Image
import shutil
from pathlib import Path
from io import BytesIO

from app.services.s3_service import S3Service
from app.services.ocr.paddle_ocr import PaddleOCRService
from app.services.table_extractor import TableExtractorService
from app.services.ai_analyzer import AIAnalyzerService
from app.core.config import settings
from app.services.vision_scanner import VisionScannerService
from app.services.dual_storage_service import DualStorageService

logger = logging.getLogger(__name__)

# Define a simple exception class for OCR errors
class PaddleOCRError(Exception):
    """Exception raised when PaddleOCR processing fails."""
    pass

# Disable PIL decompression bomb check for large images, this is a global setting
Image.MAX_IMAGE_PIXELS = None

class UnifiedOCREngine:
    """
    Orchestrates the end-to-end analysis of architectural drawings.
    """
    
    def __init__(self, task_id: str):
        """Initializes the engine with task-specific details."""
        self.task_id = task_id
        self.ocr_service = PaddleOCRService()
        self.vision_service = VisionScannerService()
        self.ai_analyzer = AIAnalyzerService()
        
        # 使用双重存储服务
        try:
            self.storage_service = DualStorageService()
            logger.info("✅ UnifiedOCREngine 使用双重存储服务")
        except Exception as e:
            logger.error(f"双重存储服务初始化失败: {e}")
            self.storage_service = None
        
        self.results = {
            "task_id": task_id,
            "original_s3_key": None,
            "processed_images": [],
            "complete_original_data": [],
            "tables_json": [],
            "qto_analysis": {}
        }

    def run_analysis_pipeline(self) -> Dict[str, Any]:
        """
        Executes the full analysis pipeline: PDF/Image -> OCR -> Table Extraction -> AI Analysis -> S3 Storage.
        This is the main entry point for Celery tasks.
        """
        logger.info(f"Task {self.task_id}: Starting analysis pipeline for {self.task_id}")
        try:
            # 1. Convert document to images
            self._convert_document_to_images()

            # 2. Process each image with OCR
            for image_path in self.image_paths:
                page_num = self.image_paths.index(image_path) + 1
                ocr_data = self._process_single_image(image_path, page_num)
                self.results["complete_original_data"].extend(ocr_data)
                self.results["processed_images"].append({"page": page_num, "image_path": os.path.basename(image_path)})
            logger.info(f"Task {self.task_id}: OCR processing completed for {len(self.image_paths)} pages.")

            # 3. Table Extraction
            logger.info(f"Task {self.task_id}: Starting table extraction...")
            all_texts = self.results["complete_original_data"]
            if all_texts:
                # Convert OCR results to the format expected by TableExtractorService
                formatted_ocr_results = []
                for text_item in all_texts:
                    bbox = text_item.get('bbox', [0, 0, 100, 30])
                    formatted_item = {
                        'text': text_item.get('text', ''),
                        'bbox_xyxy': {
                            'x_min': bbox[0],
                            'y_min': bbox[1],
                            'x_max': bbox[2],
                            'y_max': bbox[3]
                        }
                    }
                    formatted_ocr_results.append(formatted_item)
                
                table_extractor = TableExtractorService(formatted_ocr_results)
                dataframes = table_extractor.extract_tables()
                
                # Convert DataFrames to JSON format for storage
                self.results["tables_json"] = []
                for df in dataframes:
                    self.results["tables_json"].append(df.to_json(orient='split', force_ascii=False))
            else:
                self.results["tables_json"] = []
            
            logger.info(f"Task {self.task_id}: Table extraction completed. Found {len(self.results['tables_json'])} tables.")

            # 4. AI Analysis
            if self.ai_analyzer.is_available():
                logger.info(f"Task {self.task_id}: Starting AI analysis...")
                ai_input_data = { "texts": all_texts, "tables_json": self.results["tables_json"] }
                self.results["qto_analysis"] = self.ai_analyzer.generate_qto_from_data(ai_input_data)
                logger.info(f"Task {self.task_id}: AI analysis completed.")
            else:
                logger.warning(f"Task {self.task_id}: AI Analyzer is not available. Skipping.")
                self.results["qto_analysis"] = {"status": "skipped", "reason": "AI Analyzer not configured."}

            # 5. Save final results to storage
            self._save_analysis_results_to_storage()

        except Exception as e:
            logger.error(f"Task {self.task_id}: A critical error occurred in the pipeline: {e}", exc_info=True)
            self.results["error"] = str(e)
        finally:
            # 6. Cleanup
            self._cleanup_temp_files()
        
        return self.results

    def _convert_document_to_images(self):
        """Converts the input file (PDF or Image) into a list of image paths in a temporary directory."""
        logger.info(f"Task {self.task_id}: Converting document to images...")
        file_ext = os.path.splitext(self.task_id)[1].lower()
        
        if file_ext == '.pdf':
            try:
                pdf_doc = fitz.open(self.task_id)
                if pdf_doc.page_count == 0:
                    raise ValueError("PDF file is empty or corrupted.")
                for page_num in range(len(pdf_doc)):
                    page = pdf_doc.load_page(page_num)
                    pix = page.get_pixmap(dpi=300)
                    output_path = os.path.join(self.temp_dir, f"page_{page_num + 1}.png")
                    pix.save(output_path)
                    self.image_paths.append(output_path)
                logger.info(f"Task {self.task_id}: Converted PDF to {len(self.image_paths)} images.")
            except Exception as e:
                logger.error(f"Task {self.task_id}: Failed to convert PDF: {e}", exc_info=True)
                raise
        elif file_ext in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff']:
            # Copy the image to the temp directory to ensure a consistent cleanup process
            temp_image_path = os.path.join(self.temp_dir, os.path.basename(self.task_id))
            shutil.copy(self.task_id, temp_image_path)
            self.image_paths.append(temp_image_path)
            logger.info(f"Task {self.task_id}: Input is a single image, copied to temp directory.")
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")

    def _process_single_image(self, image_path: str, page_num: int) -> List[Dict[str, Any]]:
        """Runs PaddleOCR on a single image and returns structured data."""
        if not self.ocr_service.is_available():
            raise PaddleOCRError("PaddleOCR service is not initialized or available.")
        
        logger.info(f"Task {self.task_id}: Processing page {page_num} with PaddleOCR...")
        try:
            ocr_result = self.ocr_service.recognize_text(image_path, save_to_sealos=False)
            if 'error' in ocr_result:
                raise PaddleOCRError(f"OCR failed for {image_path}: {ocr_result['error']}")

            structured_results = ocr_result.get("texts", [])
            for item in structured_results:
                item['page_number'] = page_num
            return structured_results
        except Exception as e:
            logger.error(f"Task {self.task_id}: Failed to process image {image_path}: {e}", exc_info=True)
            raise

    def _save_analysis_results_to_storage(self):
        """保存完整分析结果到双重存储"""
        if not self.storage_service:
            logger.warning(f"Task {self.task_id}: 存储服务不可用，跳过结果保存")
            self.results['final_s3_key'] = "storage_service_unavailable"
            return

        final_result_key = f"results/{self.task_id}-final-analysis.json"
        
        try:
            upload_data = {
                "task_id": self.results["task_id"],
                "original_s3_key": self.results["original_s3_key"],
                "processing_summary": {
                    "image_count": len(self.results["processed_images"]),
                    "total_texts_found": len(self.results["complete_original_data"]),
                    "tables_found": len(self.results["tables_json"]),
                    "ai_analysis_status": "success" if self.results.get("qto_analysis", {}).get("success") else "failed_or_skipped"
                },
                "qto_analysis": self.results["qto_analysis"],
                "raw_ocr_data": self.results["complete_original_data"],
                "extracted_tables_json": self.results["tables_json"],
            }
            
            # 使用双重存储上传
            upload_result = self.storage_service.upload_content_sync(
                content=json.dumps(upload_data, ensure_ascii=False, indent=4),
                s3_key=final_result_key,
                content_type='application/json'
            )
            
            if upload_result.get("success"):
                self.results['final_s3_key'] = upload_result.get("final_url")
                self.results['storage_method'] = upload_result.get("storage_method")
                logger.info(f"✅ 最终分析结果保存成功: {upload_result.get('final_url')}")
            else:
                logger.error(f"最终分析结果保存失败: {upload_result.get('error')}")
                self.results['final_s3_key'] = f"upload_failed_{final_result_key}"
                
        except Exception as e:
            logger.error(f"保存最终分析结果异常: {e}")
            self.results['final_s3_key'] = f"exception_{final_result_key}"

    def _cleanup_temp_files(self):
        """Removes the temporary directory and its contents."""
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                logger.info(f"Task {self.task_id}: Successfully cleaned up temp directory: {self.temp_dir}")
        except Exception as e:
            logger.warning(f"Task {self.task_id}: Error during temp file cleanup: {e}", exc_info=True)

# Compatibility functions for potential legacy calls, can be removed later.
def create_ocr_processor(config: Optional[Dict] = None) -> None:
    """Legacy factory function. Deprecated."""
    logger.warning("Call to deprecated function create_ocr_processor. It does nothing.")
    return None

def create_component_parser() -> None:
    """Legacy factory function. Deprecated."""
    logger.warning("Call to deprecated function create_component_parser. It does nothing.")
    return None 