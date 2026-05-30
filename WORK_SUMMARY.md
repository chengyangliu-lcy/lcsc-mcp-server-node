# 嘉立创元器件 AI 查询工具 — 技术调研与设计方案

**本周：调研 + 设计 | 下周：编码实现**

---

## 一、背景

硬件开发和故障分析中，工程师需要频繁查询元器件型号、规格、数据手册和价格。期望让 AI 助手能直接接入嘉立创官方元器件库，用户用自然语言即可查询。

## 二、调研结论

### 2.1 三款 AI 工具的扩展机制

|  | Claude Code | Codex CLI | OpenCode |
|------|-------------|-----------|----------|
| MCP 支持 | 原生成熟 | 2025年加入 | 核心特性 |
| 扩展方式 | MCP + Skill(.md) | MCP | MCP |
| 注册命令 | `claude mcp add --scope user lcsc -- lcsc-mcp` | `codex mcp add lcsc -- lcsc-mcp` | 编辑 JSON 配置 |

**结论**：MCP 是三家共同标准。一个 stdio 传输的 MCP Server 即可通用。

### 2.2 元器件数据源摸底

逐一测试 2 个后端 API（支撑 3 个 MCP 工具），均可用且无需认证：

**API A：JLCPCB SMT 零件搜索**

```
POST jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList
```
- 输入：`{ keyword, pageSize, currentPage }`
- 输出：`componentCode`(C编号)、`componentNameEn`(名称)、`componentModelEn`(型号)、`componentBrandEn`(厂商)、`componentTypeEn`(分类)、`stockCount`(库存)、`componentPrices`(阶梯价格)、`dataManualUrl`(数据手册)、`componentLibraryType`(base=Basic免费/expand=Extended额外收费)、`rohsFlag`(环保标识)
- 状态：**可用**

**API B：LCSC 元器件详情**

```
GET wmsc.lcsc.com/ftps/wm/product/detail?productCode=C编号
```
- 输入：`productCode`（C 编号，如 C8734）
- 输出：`productNameEn`(名称)、`productModel`(型号)、`brandNameEn`(厂商)、`catalogName`(分类)、`stockNumber`(库存)、`minPacketNumber`(最小包装)、`productPriceList`(阶梯价格)、`pdfUrl`(数据手册直链)、`productDescEn`(描述)、`paramVOList`(技术参数列表，如 CPU 核心/主频/Flash/工作电压/温度范围等)、`productWeight`(重量)
- 状态：**可用**

**结论**：API A 负责搜索，API B 负责详情和数据手册，两者互补覆盖完整查询流程。

### 2.3 社区现状

未发现任何面向 LCSC/JLCPCB 的 MCP Server，这是空白领域。

## 三、设计方案

### 3.1 架构

```
用户自然语言 → AI 工具 (Claude Code / Codex CLI / OpenCode)
                   │ MCP Protocol (stdio)
                   ▼
              lcsc-mcp (Node.js)
                   │
         ┌─────────┼─────────┐
         ▼         ▼         ▼
    lcsc_search  lcsc_detail  lcsc_datasheet
         │           │           │
         ▼           ▼           ▼
   JLCPCB 搜索   LCSC 详情    LCSC 详情(pdfUrl提取)
```

3 个 MCP 工具，2 个后端 API，职责清晰无冗余。

### 3.2 MCP 工具详细设计

#### Tool 1：`lcsc_search` — 元器件搜索

| 项目 | 内容 |
|------|------|
| **功能** | 按关键词搜索嘉立创元器件库，结果含 C 编号、规格、价格、库存、Basic/Extended 标识等 |
| **输入** | `keyword`(关键词，如 "STM32F103")、`page`(页码)、`page_size`(每页 1-50) |
| **后端 API** | API A：JLCPCB SMT 零件搜索 |
| **输出字段** | C 编号、名称、型号、厂商、分类、库存、阶梯价格、Basic(免费贴片)/Extended(额外收费)标识、数据手册链接 |
| **典型场景** | "帮我查 STM32F103C8T6 的价格"、"JLCPCB 能贴哪些 STM32"、"有没有 0402 100nF 电容" |

> 说明：搜索同时返回 Basic/Extended 标识，用户无需关心是在查"元器件库"还是"贴片零件库"，一个工具覆盖所有搜索场景。

#### Tool 2：`lcsc_detail` — 元器件详情查询

| 项目 | 内容 |
|------|------|
| **功能** | 根据 C 编号查询元器件完整技术规格 |
| **输入** | `product_code`(C 编号，如 "C8734") |
| **后端 API** | API B：LCSC 元器件详情 |
| **输出字段** | 名称、型号、厂商、分类、库存、最小起订量、阶梯价格、数据手册 PDF 直链、RoHS 状态、产品描述、完整技术参数列表 |
| **典型场景** | "C8734 的详细参数是什么" |

#### Tool 3：`lcsc_datasheet` — 数据手册获取

| 项目 | 内容 |
|------|------|
| **功能** | 获取元器件官方数据手册 PDF 下载链接 |
| **输入** | `product_code`(C 编号，如 "C8734") |
| **后端 API** | API B：LCSC 元器件详情（提取 `pdfUrl` 字段） |
| **输出字段** | 数据手册 PDF 直链 URL |
| **典型场景** | "给我 STM32F103 的 datasheet"、"LM358 的手册在哪下载" |

### 3.3 技术选型

| 决策 | 选择 | 原因 |
|------|------|------|
| 实现语言 | TypeScript/Node.js | `npm install -g` 全局安装，只依赖 Node.js |
| 传输方式 | stdio | 三工具原生支持，无需启动 HTTP 服务 |
| 部署方式 | `npm install -g .` → 全局命令 `lcsc-mcp` | 一次安装，所有项目可用 |

### 3.4 限流策略

- 请求串行化，间隔 ≥ 3s
- 403 自动重试 2 次，指数退避（10s → 20s）
- 命中 403 后全局冷却 30s
- 结果缓存 1 小时

### 3.5 各工具配置方式

- **Claude Code**：`claude mcp add --scope user lcsc -- lcsc-mcp`
- **Codex CLI**：`codex mcp add lcsc -- lcsc-mcp`
- **OpenCode**：编辑 `~/.config/opencode/opencode.json`，写入 `mcp.lcsc`

## 四、下周实现计划

1. 搭建 TypeScript 项目，基于 `@modelcontextprotocol/sdk` 实现 MCP Server
2. 封装 2 个后端 API 调用（JLCPCB 搜索 + LCSC 详情），含限流与缓存
3. 实现 3 个 tool 的 handler 和格式化输出
4. Claude Code 注册测试
5. 编写 6 个安装脚本（3 工具 × Windows/Linux）
