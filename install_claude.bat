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

cd /d "%SCRIPT_DIR%"
if errorlevel 1 (
    echo 错误: 无法进入脚本目录
    pause
    exit /b 1
)

echo 正在安装依赖...
call npm install
if errorlevel 1 (
    echo 错误: npm install 失败
    pause
    exit /b 1
)

echo 正在构建 lcsc-mcp-server...
call npm run build
if errorlevel 1 (
    echo 错误: npm run build 失败
    pause
    exit /b 1
)

echo 正在全局安装 lcsc-mcp-server...
call npm install -g .
if errorlevel 1 (
    echo 错误: npm 全局安装失败
    pause
    exit /b 1
)

echo 注册到 Claude Code...
claude mcp add --scope user lcsc -- lcsc-mcp
if errorlevel 1 (
    echo 错误: Claude Code MCP 注册失败
    pause
    exit /b 1
)

echo.
echo 安装完成！重启 Claude Code 后所有项目均可使用。
pause
