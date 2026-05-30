#!/bin/bash
# 一键安装 LCSC MCP Server 到 Codex CLI（全局生效）
# Usage: bash install_codex.sh

echo "=== LCSC MCP Server - Codex CLI 全局安装 ==="

if ! command -v node &> /dev/null; then
    echo "错误: 未找到 node，请先安装 Node.js >= 18"
    exit 1
fi

if ! command -v codex &> /dev/null; then
    echo "错误: 未找到 codex，请先安装 OpenAI Codex CLI"
    exit 1
fi

# 全局安装
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "正在全局安装 lcsc-mcp-server..."
cd "$SCRIPT_DIR" && npm install -g . || exit 1

# 写入 Codex 配置（~/.codex/config.toml）
echo "正在注册到 Codex CLI..."
if codex mcp get lcsc >/dev/null 2>&1; then
    echo "已存在 lcsc MCP 配置，正在更新..."
    codex mcp remove lcsc || exit 1
fi

codex mcp add lcsc -- lcsc-mcp || exit 1

echo ""
echo "安装完成！重启 Codex CLI 后所有项目均可使用。"
