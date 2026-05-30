#!/bin/bash
# 一键安装 LCSC MCP Server 到 OpenCode（全局生效）
# Usage: bash install_opencode.sh

CONFIG_DIR="$HOME/.config/opencode"
CONFIG_FILE="$CONFIG_DIR/opencode.json"

echo "=== LCSC MCP Server - OpenCode 全局安装 ==="

if ! command -v node &> /dev/null; then
    echo "错误: 未找到 node，请先安装 Node.js >= 18"
    exit 1
fi

# 全局安装
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "正在全局安装 lcsc-mcp-server..."
cd "$SCRIPT_DIR" && npm install -g .

# 写入 OpenCode 配置
mkdir -p "$CONFIG_DIR"
if [ -f "$CONFIG_FILE" ]; then
    python3 -c "
import json
with open('$CONFIG_FILE') as f: c = json.load(f)
c.setdefault('mcp', {})['lcsc'] = {'type': 'local', 'command': ['lcsc-mcp'], 'enabled': True}
with open('$CONFIG_FILE', 'w') as f: json.dump(c, f, indent=2)
print('已更新 $CONFIG_FILE')
" 2>/dev/null || echo '{"$schema":"https://opencode.ai/config.json","mcp":{"lcsc":{"type":"local","command":["lcsc-mcp"],"enabled":true}}}' > "$CONFIG_FILE"
else
    echo '{"$schema":"https://opencode.ai/config.json","mcp":{"lcsc":{"type":"local","command":["lcsc-mcp"],"enabled":true}}}' > "$CONFIG_FILE"
    echo "已创建 $CONFIG_FILE"
fi

echo ""
echo "安装完成！重启 OpenCode 后所有项目均可使用。"
