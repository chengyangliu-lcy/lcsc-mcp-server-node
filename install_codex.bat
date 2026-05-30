@echo off
chcp 65001 >nul 2>&1
setlocal

set SCRIPT_DIR=%~dp0

echo === LCSC MCP Server - Codex CLI 全局安装 ===

where node >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 node，请先安装 Node.js ^>= 18
    pause
    exit /b 1
)

where codex >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 codex，请先安装 OpenAI Codex CLI
    pause
    exit /b 1
)

echo 正在全局安装 lcsc-mcp-server...
cd /d "%SCRIPT_DIR%" && call npm install -g .
if errorlevel 1 (
    echo 错误: npm 全局安装失败
    pause
    exit /b 1
)

echo 正在注册到 Codex CLI...
codex mcp get lcsc >nul 2>&1
if not errorlevel 1 (
    echo 已存在 lcsc MCP 配置，正在更新...
    codex mcp remove lcsc
    if errorlevel 1 (
        echo 错误: 移除旧的 Codex MCP 配置失败
        pause
        exit /b 1
    )
)

codex mcp add lcsc -- lcsc-mcp
if errorlevel 1 (
    echo 错误: Codex MCP 注册失败
    pause
    exit /b 1
)

echo.
echo 安装完成！重启 Codex CLI 后所有项目均可使用。
pause
