# GameTest AI 项目启动脚本

Set-Location $PSScriptRoot

# 统一 PowerShell 编码
$utf8 = New-Object System.Text.UTF8Encoding($false)

[Console]::InputEncoding = $utf8
[Console]::OutputEncoding = $utf8
$OutputEncoding = $utf8

# 启用 Python UTF-8 模式
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

# 启动 Streamlit
.\.venv\Scripts\python.exe -m streamlit run .\app.py