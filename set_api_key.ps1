# 设置 OpenAI API Key
Write-Host "设置 OpenAI API Key..." -ForegroundColor Green

# 请将下面的 YOUR_COMPLETE_API_KEY 替换为您完整的 API key (以V6M6结尾)
$env:OPENAI_API_KEY = "sk-proj-YOUR_COMPLETE_API_KEY_ENDING_WITH_V6M6"

# 显示当前设置
$keyLength = $env:OPENAI_API_KEY.Length
$lastFour = $env:OPENAI_API_KEY.Substring($keyLength - 4)
Write-Host "当前 API Key 末尾4位: $lastFour" -ForegroundColor Cyan

Write-Host ""
Write-Host "API Key 已设置。现在可以启动服务了。" -ForegroundColor Green
Write-Host "" 