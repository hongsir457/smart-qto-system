@echo off
echo 设置 OpenAI API Key...

REM 请将下面的 YOUR_COMPLETE_API_KEY 替换为您完整的 API key (以V6M6结尾)
set OPENAI_API_KEY=sk-proj-YOUR_COMPLETE_API_KEY_ENDING_WITH_V6M6

echo 当前 API Key 末尾4位: %OPENAI_API_KEY:~-4%
echo.
echo API Key 已设置。现在可以启动服务了。
echo.
pause 