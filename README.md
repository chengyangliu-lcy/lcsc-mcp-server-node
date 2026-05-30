# LCSC MCP Server

嘉立创(LCSC/JLCPCB)电子元器件查询 MCP Server。让 AI 助手能够搜索元器件、查看技术规格、获取数据手册。

兼容 Claude Code、OpenAI Codex CLI、OpenCode 三个 AI 编码助手。

## 功能

| 工具 | 说明 |
|------|------|
| `lcsc_search` | 按关键词搜索 LCSC 元器件库 |
| `lcsc_detail` | 按 C 编号获取元器件详细规格 |
| `lcsc_datasheet` | 获取元器件数据手册 PDF 链接 |

## 前置条件

- Node.js >= 18

## 安装

### 1. 全局安装包

```bash
cd lcsc-mcp-server-node
npm install -g .
```

安装后全局命令 `lcsc-mcp` 即可使用。

### 2. 注册到 AI 工具

#### Claude Code（全局生效，所有项目可用）

```bash
claude mcp add --scope user lcsc -- lcsc-mcp
```

#### OpenAI Codex CLI

使用 Codex CLI 注册 MCP Server：

```bash
codex mcp add lcsc -- lcsc-mcp
```

Codex 会写入 `~/.codex/config.toml`。不要写 `~/.codex/config.json`，新版 Codex CLI 不读取该文件。

#### OpenCode

编辑 `~/.config/opencode/opencode.json`（没有则创建）：

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "lcsc": {
      "type": "local",
      "command": ["lcsc-mcp"],
      "enabled": true
    }
  }
}
```

### 3. 重启 AI 工具

安装完成后重启对应的 AI 工具即可使用。

## 一键安装脚本

也可以运行安装脚本自动完成上述步骤：

```bash
# Linux / Mac
bash install_claude.sh      # Claude Code
bash install_codex.sh       # Codex CLI
bash install_opencode.sh    # OpenCode

# Windows
install_claude.bat          # Claude Code
install_codex.bat           # Codex CLI
install_opencode.bat        # OpenCode
```

## 使用示例

在 AI 助手中直接用自然语言询问：

- "帮我查一下 STM32F103C8T6 在嘉立创的价格和库存"
- "C123456 的详细参数是什么？"
- "给我 LM358 的 datasheet 链接"
- "JLCPCB 有哪些 0402 100nF 电容可以贴片？"

## 注意事项

- 嘉立创 API 有频率限制，工具内置了限速（2秒/次）和 403 自动重试机制
- 请勿并行调用多个搜索请求，逐个调用更稳妥
- 价格和库存实时变化，以官网为准

## 本地开发

```bash
npm run dev    # tsx 热重载开发
npm run build  # 编译 TypeScript
npm start      # 运行编译后的版本
```
