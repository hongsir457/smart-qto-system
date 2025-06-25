# 智能工程量计算系统 - 云存储依赖安装脚本
# 安装Sealos云存储所需的Python包

Write-Host "🚀 安装云存储依赖包..." -ForegroundColor Green

# 检查Python环境
$pythonCmd = "python"
if (Get-Command python -ErrorAction SilentlyContinue) {
    Write-Host "✅ 找到Python: $(python --version)" -ForegroundColor Green
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $pythonCmd = "python3"
    Write-Host "✅ 找到Python3: $(python3 --version)" -ForegroundColor Green
} else {
    Write-Host "❌ 未找到Python，请先安装Python 3.8+" -ForegroundColor Red
    exit 1
}

# 检查pip
$pipCmd = "pip"
if (Get-Command pip -ErrorAction SilentlyContinue) {
    Write-Host "✅ 找到pip: $(pip --version)" -ForegroundColor Green
} elseif (Get-Command pip3 -ErrorAction SilentlyContinue) {
    $pipCmd = "pip3"
    Write-Host "✅ 找到pip3: $(pip3 --version)" -ForegroundColor Green
} else {
    Write-Host "❌ 未找到pip，请先安装pip" -ForegroundColor Red
    exit 1
}

# 安装云存储相关依赖
Write-Host "`n📦 安装云存储依赖包..." -ForegroundColor Yellow

$packages = @(
    "boto3>=1.26.0",
    "aiofiles>=23.0.0", 
    "aiohttp>=3.8.0",
    "botocore>=1.29.0"
)

foreach ($package in $packages) {
    Write-Host "  安装 $package..." -ForegroundColor Cyan
    try {
        & $pipCmd install $package --upgrade
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✅ $package 安装成功" -ForegroundColor Green
        } else {
            Write-Host "  ❌ $package 安装失败" -ForegroundColor Red
        }
    } catch {
        Write-Host "  ❌ $package 安装异常: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# 更新requirements.txt
Write-Host "`n📝 更新requirements.txt..." -ForegroundColor Yellow

$requirementsFile = "requirements.txt"
$newDeps = @(
    "boto3>=1.26.0",
    "aiofiles>=23.0.0",
    "aiohttp>=3.8.0", 
    "botocore>=1.29.0"
)

if (Test-Path $requirementsFile) {
    $content = Get-Content $requirementsFile -Raw
    $updated = $false
    
    foreach ($dep in $newDeps) {
        $packageName = $dep.Split(">=")[0]
        if ($content -notmatch "^$packageName") {
            Add-Content $requirementsFile "`n$dep"
            Write-Host "  ✅ 添加 $dep 到 requirements.txt" -ForegroundColor Green
            $updated = $true
        } else {
            Write-Host "  ℹ️  $packageName 已存在于 requirements.txt" -ForegroundColor Blue
        }
    }
    
    if ($updated) {
        Write-Host "✅ requirements.txt 已更新" -ForegroundColor Green
    }
} else {
    Write-Host "❌ 未找到 requirements.txt 文件" -ForegroundColor Red
}

# 检查安装结果
Write-Host "`n🔍 验证安装结果..." -ForegroundColor Yellow

$testScript = @"
import sys
try:
    import boto3
    print("✅ boto3:", boto3.__version__)
except ImportError as e:
    print("❌ boto3 导入失败:", e)
    sys.exit(1)

try:
    import aiofiles
    print("✅ aiofiles: 已安装")
except ImportError as e:
    print("❌ aiofiles 导入失败:", e)
    sys.exit(1)

try:
    import aiohttp
    print("✅ aiohttp:", aiohttp.__version__)
except ImportError as e:
    print("❌ aiohttp 导入失败:", e)
    sys.exit(1)

try:
    import botocore
    print("✅ botocore:", botocore.__version__)
except ImportError as e:
    print("❌ botocore 导入失败:", e)
    sys.exit(1)

print("🎉 所有云存储依赖包安装成功！")
"@

$testScript | & $pythonCmd

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n🎉 云存储依赖安装完成！" -ForegroundColor Green
    Write-Host "`n下一步:" -ForegroundColor Yellow
    Write-Host "  1. 运行云存储配置向导: python setup_cloud_storage.py" -ForegroundColor Cyan
    Write-Host "  2. 或手动编辑 .env 文件配置Sealos存储" -ForegroundColor Cyan
    Write-Host "  3. 重启服务以应用新配置" -ForegroundColor Cyan
} else {
    Write-Host "`n❌ 依赖验证失败，请检查安装" -ForegroundColor Red
    exit 1
}

Write-Host "`n按任意键退出..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown") 