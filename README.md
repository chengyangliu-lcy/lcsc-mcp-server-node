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
npm install
npm run build
npm install -g .
```

`npm run build` 会生成 `dist/index.js`。安装后全局命令 `lcsc-mcp` 即可使用。

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

验证是否注册成功：

```bash
codex mcp list
```

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

## 工具测试用例

安装并重启 AI 工具后，可以用下面的提示词测试 MCP 是否正常工作。嘉立创接口会限流，建议每次只运行一个用例，等待几秒后再运行下一个。

### `lcsc_search`：搜索元器件

用途：按关键词搜索 LCSC/JLCPCB 元器件库，返回 C 编号、型号、厂商、库存、价格、Basic/Extended 标识和数据手册链接。

参数：

| 参数 | 类型 | 说明 |
|------|------|------|
| `keyword` | string | 搜索关键词，例如 `STM32F103`、`100nF 0402`、`LM358` |
| `page` | number | 页码，从 `1` 开始，默认 `1` |
| `page_size` | number | 每页数量，范围 `1-50`，默认 `10` |

自然语言测试：

```text
搜索 STM32F103，显示前 5 个嘉立创/JLCPCB 元器件结果，包含 C 编号、库存、价格和 datasheet。
```

直接工具调用参数示例：

```json
{
  "keyword": "STM32F103",
  "page": 1,
  "page_size": 5
}
```

预期结果：返回类似 `共找到 ... 个结果` 的列表，每条结果包含 `[Cxxxxxx]`、型号、厂商、库存、阶梯价格；如果有数据手册，会显示链接。

### `lcsc_detail`：查询元器件详情

用途：根据 LCSC C 编号查询单个元器件的完整信息，包括技术参数、阶梯价格、库存、起订量和数据手册链接。

参数：

| 参数 | 类型 | 说明 |
|------|------|------|
| `product_code` | string | LCSC C 编号，例如 `C123456`；只输入数字时会自动补 `C` |

自然语言测试：

```text
查询 C2936108 的详细信息，列出型号、厂商、库存、价格、datasheet 和主要技术参数。
```

直接工具调用参数示例：

```json
{
  "product_code": "C2936108"
}
```

也可以只传数字：

```json
{
  "product_code": "2936108"
}
```

预期结果：返回以 `=== C2936108 ===` 开头的详情文本，包含名称、型号、厂商、分类、库存、最小起订、价格、数据手册和技术参数。若编号不存在，会返回 `未找到该元器件的详细信息。`

### `lcsc_datasheet`：获取数据手册链接

用途：根据 LCSC C 编号获取元器件 PDF 数据手册下载链接。

参数：

| 参数 | 类型 | 说明 |
|------|------|------|
| `product_code` | string | LCSC C 编号，例如 `C2936108`；只输入数字时会自动补 `C` |

自然语言测试：

```text
获取 C2936108 的 datasheet 下载链接。
```

直接工具调用参数示例：

```json
{
  "product_code": "C2936108"
}
```

预期结果：如果该器件有数据手册，会返回 `数据手册下载链接: https://...`；如果没有，会返回 `该元器件暂无数据手册链接。`

## 注意事项

- 嘉立创 API 有频率限制，工具内置了限速（3秒/次）和 403 自动重试机制
- 请勿并行调用多个搜索请求，逐个调用更稳妥
- 价格和库存实时变化，以官网为准

## 本地开发

```bash
npm run dev    # tsx 热重载开发
npm run build  # 编译 TypeScript
npm start      # 运行编译后的版本
```
