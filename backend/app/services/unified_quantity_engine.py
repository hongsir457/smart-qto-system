#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified Quantity Calculation Engine
This engine is the sole entry point for quantity calculation, using the robust QuantityCalculator service.
"""

import logging
import time
from typing import Dict, Any

# 导入已经优化的、健壮的计算器
from .quantity_calculator import QuantityCalculator

logger = logging.getLogger(__name__)

class UnifiedQuantityEngine:
    """Unified Quantity Calculation Engine - a robust wrapper around QuantityCalculator."""
    
    def __init__(self):
        """Initialize the calculation engine."""
        self.calculator = QuantityCalculator()
        logger.info("✅ Unified Quantity Engine initialized, now using QuantityCalculator.")
    
    def calculate_quantities(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate quantities using the robust QuantityCalculator.
        This is the single, reliable entry point for all quantity calculations.
        """
        if not isinstance(analysis_result, dict):
            logger.error(f"❌ Invalid input for quantity calculation: expected a dict, got {type(analysis_result)}")
            return {
                'status': 'error',
                'error': 'Invalid input data format for quantity calculation.'
            }
        
        logger.info("🚀 Starting quantity calculation via QuantityCalculator...")
        start_time = time.time()
        
        try:
            # 直接调用已经优化过的、健壮的计算器
            calculation_result = self.calculator.process_recognition_results(analysis_result)
            
            total_time = time.time() - start_time
            calculation_result['calculation_time'] = total_time
            
            if calculation_result.get('status') == 'success':
                logger.info(f"✅ Quantity calculation completed successfully in {total_time:.2f} seconds.")
            else:
                logger.warning(f"⚠️ Quantity calculation finished with errors in {total_time:.2f} seconds. "
                               f"Error: {calculation_result.get('error_message')}")

            return calculation_result
            
        except Exception as e:
            logger.error(f"❌ An unexpected critical error occurred in QuantityCalculator: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'error': f"Critical unexpected error: {str(e)}",
                'calculation_time': time.time() - start_time
            } 