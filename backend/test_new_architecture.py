#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试新架构的完整数据流程
模拟从文件上传到导出的完整流程
"""

import requests
import time
import json
import logging
import os

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ArchitectureTest:
    """新架构测试类"""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.headers = {}
        self.test_results = []
    
    def run_complete_test(self):
        """运行完整的架构测试"""
        logger.info("🚀 开始新架构完整测试")
        print("=" * 80)
        
        try:
            # 1. 测试用户认证
            if not self._test_authentication():
                return False
            
            # 2. 测试文件上传 (S3集成)
            drawing_id = self._test_file_upload()
            if not drawing_id:
                return False
            
            # 3. 测试Celery任务处理
            if not self._test_celery_processing(drawing_id):
                return False
            
            # 4. 测试工程量导出
            if not self._test_export_functionality(drawing_id):
                return False
            
            # 5. 测试数据一致性
            if not self._test_data_consistency(drawing_id):
                return False
            
            self._print_summary()
            return True
            
        except Exception as e:
            logger.error(f"❌ 测试过程中发生异常: {str(e)}")
            return False
    
    def _test_authentication(self):
        """测试用户认证"""
        logger.info("1️⃣ 测试用户认证...")
        
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/auth/login",
                data={
                    "username": "testuser",
                    "password": "testpass123"
                }
            )
            
            if response.status_code == 200:
                token = response.json()["access_token"]
                self.headers = {"Authorization": f"Bearer {token}"}
                logger.info("✅ 用户认证成功")
                self.test_results.append(("认证", "✅ 成功"))
                return True
            else:
                logger.error(f"❌ 认证失败: {response.status_code}")
                self.test_results.append(("认证", f"❌ 失败 ({response.status_code})"))
                return False
                
        except Exception as e:
            logger.error(f"❌ 认证异常: {str(e)}")
            self.test_results.append(("认证", f"❌ 异常: {str(e)}"))
            return False
    
    def _test_file_upload(self):
        """测试文件上传 (S3集成)"""
        logger.info("2️⃣ 测试文件上传 (S3集成)...")
        
        try:
            # 创建测试文件
            test_content = b"Test PDF content for new architecture"
            files = {
                'file': ('test_architecture.pdf', test_content, 'application/pdf')
            }
            
            response = requests.post(
                f"{self.base_url}/api/v1/drawings/upload",
                files=files,
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                drawing_id = data.get("id")
                task_id = data.get("task_id")
                
                logger.info(f"✅ 文件上传成功，图纸ID: {drawing_id}, 任务ID: {task_id}")
                self.test_results.append(("S3上传", "✅ 成功"))
                
                # 验证图纸状态
                if data.get("status") == "pending":
                    logger.info("✅ 图纸状态正确设置为 pending")
                    self.test_results.append(("初始状态", "✅ pending"))
                else:
                    logger.warning(f"⚠️ 图纸状态异常: {data.get('status')}")
                    self.test_results.append(("初始状态", f"⚠️ {data.get('status')}"))
                
                return drawing_id
            else:
                logger.error(f"❌ 文件上传失败: {response.status_code}")
                self.test_results.append(("S3上传", f"❌ 失败 ({response.status_code})"))
                return None
                
        except Exception as e:
            logger.error(f"❌ 文件上传异常: {str(e)}")
            self.test_results.append(("S3上传", f"❌ 异常: {str(e)}"))
            return None
    
    def _test_celery_processing(self, drawing_id):
        """测试Celery任务处理"""
        logger.info("3️⃣ 测试Celery任务处理...")
        
        try:
            max_wait_time = 60  # 最多等待60秒
            check_interval = 3  # 每3秒检查一次
            
            for i in range(0, max_wait_time, check_interval):
                time.sleep(check_interval)
                
                # 检查图纸状态
                response = requests.get(
                    f"{self.base_url}/api/v1/drawings/{drawing_id}",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    status = data.get("status")
                    
                    logger.info(f"第 {i+check_interval} 秒 - 状态: {status}")
                    
                    if status == "completed":
                        logger.info("✅ Celery任务处理完成")
                        self.test_results.append(("Celery处理", "✅ 完成"))
                        
                        # 验证数据完整性
                        self._verify_processing_results(data)
                        return True
                        
                    elif status == "failed":
                        error_msg = data.get("error_message", "未知错误")
                        logger.error(f"❌ Celery任务失败: {error_msg}")
                        self.test_results.append(("Celery处理", f"❌ 失败: {error_msg}"))
                        return False
                        
                    elif status == "processing":
                        logger.info("🔄 任务处理中...")
                        
                else:
                    logger.error(f"❌ 获取图纸状态失败: {response.status_code}")
            
            logger.error("⏰ Celery任务处理超时")
            self.test_results.append(("Celery处理", "⏰ 超时"))
            return False
            
        except Exception as e:
            logger.error(f"❌ Celery处理测试异常: {str(e)}")
            self.test_results.append(("Celery处理", f"❌ 异常: {str(e)}"))
            return False
    
    def _verify_processing_results(self, drawing_data):
        """验证处理结果"""
        logger.info("🔍 验证处理结果...")
        
        # 检查必要字段
        required_fields = ["recognition_results", "quantity_results", "components_count"]
        
        for field in required_fields:
            if field in drawing_data and drawing_data[field] is not None:
                logger.info(f"✅ {field} 字段存在")
                self.test_results.append((f"字段:{field}", "✅ 存在"))
            else:
                logger.warning(f"⚠️ {field} 字段缺失")
                self.test_results.append((f"字段:{field}", "⚠️ 缺失"))
        
        # 验证工程量结果结构
        quantity_results = drawing_data.get("quantity_results", {})
        if quantity_results:
            if "total_summary" in quantity_results:
                summary = quantity_results["total_summary"]
                logger.info(f"✅ 工程量汇总: 总构件数={summary.get('total_count', 0)}")
                self.test_results.append(("工程量汇总", "✅ 正常"))
            
            if "quantities" in quantity_results:
                quantities = quantity_results["quantities"]
                logger.info(f"✅ 构件分类: {list(quantities.keys())}")
                self.test_results.append(("构件分类", f"✅ {len(quantities)}类"))
    
    def _test_export_functionality(self, drawing_id):
        """测试导出功能"""
        logger.info("4️⃣ 测试导出功能...")
        
        try:
            # 测试导出预览
            response = requests.get(
                f"{self.base_url}/api/v1/drawings/{drawing_id}/export/preview",
                headers=self.headers
            )
            
            if response.status_code == 200:
                preview_data = response.json()
                logger.info("✅ 导出预览成功")
                self.test_results.append(("导出预览", "✅ 成功"))
                
                # 验证预览数据
                if preview_data.get("exportable"):
                    logger.info("✅ 数据可导出")
                    self.test_results.append(("可导出性", "✅ 是"))
                else:
                    logger.warning("⚠️ 数据不可导出")
                    self.test_results.append(("可导出性", "⚠️ 否"))
                
            else:
                logger.error(f"❌ 导出预览失败: {response.status_code}")
                self.test_results.append(("导出预览", f"❌ 失败 ({response.status_code})"))
                return False
            
            # 测试Excel导出
            response = requests.get(
                f"{self.base_url}/api/v1/drawings/{drawing_id}/export",
                headers=self.headers
            )
            
            if response.status_code == 200:
                if 'application/vnd.openxmlformats' in response.headers.get('content-type', ''):
                    logger.info("✅ Excel导出成功")
                    self.test_results.append(("Excel导出", "✅ 成功"))
                    return True
                else:
                    logger.warning("⚠️ Excel导出格式异常")
                    self.test_results.append(("Excel导出", "⚠️ 格式异常"))
                    return False
            else:
                logger.error(f"❌ Excel导出失败: {response.status_code}")
                self.test_results.append(("Excel导出", f"❌ 失败 ({response.status_code})"))
                return False
                
        except Exception as e:
            logger.error(f"❌ 导出功能测试异常: {str(e)}")
            self.test_results.append(("导出功能", f"❌ 异常: {str(e)}"))
            return False
    
    def _test_data_consistency(self, drawing_id):
        """测试数据一致性"""
        logger.info("5️⃣ 测试数据一致性...")
        
        try:
            # 获取图纸详细信息
            response = requests.get(
                f"{self.base_url}/api/v1/drawings/{drawing_id}",
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # 检查S3相关字段
                s3_fields = ["s3_key", "s3_url", "s3_bucket"]
                s3_consistent = all(field in data and data[field] for field in s3_fields)
                
                if s3_consistent:
                    logger.info("✅ S3数据一致性检查通过")
                    self.test_results.append(("S3一致性", "✅ 通过"))
                else:
                    logger.warning("⚠️ S3数据一致性检查未通过")
                    self.test_results.append(("S3一致性", "⚠️ 未通过"))
                
                # 检查任务相关字段
                task_fields = ["task_id", "celery_task_id"]
                task_consistent = all(field in data and data[field] for field in task_fields)
                
                if task_consistent:
                    logger.info("✅ 任务数据一致性检查通过")
                    self.test_results.append(("任务一致性", "✅ 通过"))
                else:
                    logger.warning("⚠️ 任务数据一致性检查未通过")
                    self.test_results.append(("任务一致性", "⚠️ 未通过"))
                
                return True
            else:
                logger.error(f"❌ 获取图纸信息失败: {response.status_code}")
                self.test_results.append(("数据一致性", f"❌ 失败 ({response.status_code})"))
                return False
                
        except Exception as e:
            logger.error(f"❌ 数据一致性测试异常: {str(e)}")
            self.test_results.append(("数据一致性", f"❌ 异常: {str(e)}"))
            return False
    
    def _print_summary(self):
        """打印测试总结"""
        print("\n" + "=" * 80)
        print("📊 新架构测试总结")
        print("=" * 80)
        
        success_count = sum(1 for _, result in self.test_results if result.startswith("✅"))
        total_count = len(self.test_results)
        
        print(f"📈 测试统计: {success_count}/{total_count} 项通过")
        print("\n📋 详细结果:")
        
        for test_name, result in self.test_results:
            print(f"  {test_name:<15} : {result}")
        
        print("\n" + "=" * 80)
        
        if success_count == total_count:
            print("🎉 所有测试通过！新架构运行正常")
        else:
            print("⚠️ 部分测试未通过，需要进一步检查")
        
        print("=" * 80)

def main():
    """主函数"""
    print("🚀 智能工程量计算系统 - 新架构测试")
    print("测试数据流程：文件上传 → S3存储 → Celery处理 → 工程量计算 → 导出")
    print("=" * 80)
    
    tester = ArchitectureTest()
    success = tester.run_complete_test()
    
    if success:
        print("\n✅ 新架构测试完成！")
        return 0
    else:
        print("\n❌ 新架构测试失败！")
        return 1

if __name__ == "__main__":
    exit(main())