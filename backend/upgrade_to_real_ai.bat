@echo off
echo ========================================
echo 🚀 升级到真实AI识别系统
echo ========================================

echo 📦 安装AI处理依赖...
pip install -r requirements_ai.txt

echo 🔧 设置环境变量（可选）...
echo 如需使用真实的GPT-4分析，请设置以下环境变量：
echo set OPENAI_API_KEY=your_openai_api_key_here

echo ✅ 升级完成！

echo ========================================
echo 🎯 现在您拥有以下真实AI功能：
echo ========================================
echo ✅ PaddleOCR - 真实图纸文字识别
echo ✅ GPT-4 - 智能构件分析（需要API密钥）
echo ✅ YOLOv8 - 构件边界检测（待开发）
echo ✅ 工程量自动计算

echo ========================================
echo 📖 使用说明：
echo ========================================
echo 1. 不设置 OPENAI_API_KEY：使用 PaddleOCR + 模拟GPT分析
echo 2. 设置 OPENAI_API_KEY：使用 PaddleOCR + 真实GPT-4分析

echo 🔄 重启后端服务以加载新的AI模块...
pause 