# PowerShell Script to Set S3 API Keys in .env file

# Set target directory to 'backend'
$BackendDir = "backend"
if (-not (Test-Path -Path $BackendDir)) {
    Write-Host "错误: 'backend' 目录未找到。" -ForegroundColor Red
    exit 1
}

$EnvFile = Join-Path -Path $BackendDir -ChildPath ".env"

Write-Host "--- S3 访问凭证设置 ---" -ForegroundColor Yellow

# Prompt for credentials
$AccessKey = Read-Host "请输入您的 S3 Access Key"
$SecretKey = Read-Host "请输入您的 S3 Secret Key"

if (-not $AccessKey -or -not $SecretKey) {
    Write-Host "错误: Access Key 和 Secret Key 不能为空。" -ForegroundColor Red
    exit 1
}

# Prepare new content
$AccessKeyLine = "S3_ACCESS_KEY='$AccessKey'"
$SecretKeyLine = "S3_SECRET_KEY='$SecretKey'"

# Update or add the keys in the .env file
if (Test-Path $EnvFile) {
    $content = Get-Content $EnvFile
    $newContent = @()
    $accessKeyUpdated = $false
    $secretKeyUpdated = $false

    foreach ($line in $content) {
        if ($line.StartsWith("S3_ACCESS_KEY=")) {
            $newContent += $AccessKeyLine
            $accessKeyUpdated = $true
        } elseif ($line.StartsWith("S3_SECRET_KEY=")) {
            $newContent += $SecretKeyLine
            $secretKeyUpdated = $true
        } else {
            $newContent += $line
        }
    }

    if (-not $accessKeyUpdated) {
        $newContent += $AccessKeyLine
    }
    if (-not $secretKeyUpdated) {
        $newContent += $SecretKeyLine
    }

    Set-Content -Path $EnvFile -Value $newContent -Encoding Utf8
} else {
    # Create a new .env file
    Set-Content -Path $EnvFile -Value "$AccessKeyLine`n$SecretKeyLine" -Encoding Utf8
}

Write-Host "✅ S3凭证已成功更新到 '$EnvFile'" -ForegroundColor Green