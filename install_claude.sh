#!/bin/bash
# 一键安装 LCSC MCP Server 到 Claude Code（全局生效）
# Usage: bash install_claude.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== LCSC MCP Server - Claude Code 全局安装 ==="

# 检查 node
if ! command -v node &> /dev/null; then
    echo "错误: 未找到 node，请先安装 Node.js >= 18"
    exit 1
fi

# 安装依赖、构建并全局安装 npm 包
cd "$SCRIPT_DIR" || exit 1
echo "正在安装依赖..."
npm install || exit 1

echo "正在构建 lcsc-mcp-server..."
npm run build || exit 1

echo "正在全局安装 lcsc-mcp-server..."
npm install -g . || exit 1

# 注册到 Claude Code（全局 scope）
echo "注册到 Claude Code..."
claude mcp add --scope user lcsc -- lcsc-mcp || exit 1

echo ""
echo "安装完成！重启 Claude Code 后所有项目均可使用。"
