@echo off
chcp 65001 >nul 2>&1
setlocal

set SCRIPT_DIR=%~dp0
set CONFIG_DIR=%USERPROFILE%\.config\opencode
set CONFIG_FILE=%CONFIG_DIR%\opencode.json

echo === LCSC MCP Server - OpenCode 全局安装 ===

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

if not exist "%CONFIG_DIR%" mkdir "%CONFIG_DIR%"

if exist "%CONFIG_FILE%" (
    python -c "import json;p=r'%CONFIG_FILE%';c=json.load(open(p));c.setdefault('mcp',{})['lcsc']={'type':'local','command':['lcsc-mcp'],'enabled':True};json.dump(c,open(p,'w'),indent=2);print('已更新')"
) else (
    python -c "import json;json.dump({'$schema':'https://opencode.ai/config.json','mcp':{'lcsc':{'type':'local','command':['lcsc-mcp'],'enabled':True}}},open(r'%CONFIG_FILE%','w'),indent=2);print('已创建')"
)

echo.
echo 安装完成！重启 OpenCode 后所有项目均可使用。
pause
