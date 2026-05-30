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

# 全局安装 npm 包
echo "正在全局安装 lcsc-mcp-server..."
cd "$SCRIPT_DIR" && npm install -g .

# 注册到 Claude Code（全局 scope）
echo "注册到 Claude Code..."
claude mcp add --scope user lcsc -- lcsc-mcp

echo ""
echo "安装完成！重启 Claude Code 后所有项目均可使用。"
