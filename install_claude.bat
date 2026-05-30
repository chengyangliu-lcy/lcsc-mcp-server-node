@echo off
chcp 65001 >nul 2>&1
setlocal

set SCRIPT_DIR=%~dp0

echo === LCSC MCP Server - Claude Code 全局安装 ===

where node >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 node，请先安装 Node.js ^>= 18
    pause
    exit /b 1
)

echo 正在全局安装 lcsc-mcp-server...
cd /d "%SCRIPT_DIR%" && call npm install -g .

echo 注册到 Claude Code...
claude mcp add --scope user lcsc -- lcsc-mcp

echo.
echo 安装完成！重启 Claude Code 后所有项目均可使用。
pause
