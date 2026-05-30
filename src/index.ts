#!/usr/bin/env node

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

// ── Rate limiter ────────────────────────────────────────────────────────────

let lastRequestTime = 0;
let cooldownUntil = 0; // 全局冷却期：任一次 403 后，所有请求等待到此时间
const MIN_INTERVAL_MS = 3000;     // 正常请求间隔 3s
const MAX_RETRIES = 2;            // 最多重试 2 次
const BACKOFF_BASE_MS = 10000;    // 首次退避 10s
const COOLDOWN_AFTER_403_MS = 30000; // 命中 403 后的全局冷却 30s

async function rateLimitedFetch(
  url: string,
  init?: RequestInit
): Promise<Response> {
  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    const now = Date.now();

    // 全局冷却
    if (cooldownUntil > now) {
      const wait = cooldownUntil - now;
      console.error(`[lcsc-mcp] 全局冷却中，等待 ${(wait / 1000).toFixed(1)}s...`);
      await sleep(wait);
    }

    // 请求间隔
    const sinceLast = Date.now() - lastRequestTime;
    if (sinceLast < MIN_INTERVAL_MS) {
      await sleep(MIN_INTERVAL_MS - sinceLast);
    }
    lastRequestTime = Date.now();

    const resp = await fetch(url, init);

    if (resp.status === 403) {
      cooldownUntil = Date.now() + COOLDOWN_AFTER_403_MS;
      if (attempt < MAX_RETRIES) {
        const backoff = BACKOFF_BASE_MS * 2 ** attempt;
        console.error(
          `[lcsc-mcp] 403 (attempt ${attempt + 1}/${MAX_RETRIES + 1}), 退避 ${backoff / 1000}s, 全局冷却 ${COOLDOWN_AFTER_403_MS / 1000}s`
        );
        await sleep(backoff);
        continue;
      }
      throw new RateLimitError(COOLDOWN_AFTER_403_MS);
    }

    if (resp.status === 429) {
      cooldownUntil = Date.now() + COOLDOWN_AFTER_403_MS;
      const retryAfter =
        parseInt(resp.headers.get("Retry-After") || "30", 10) * 1000;
      throw new RateLimitError(Math.max(retryAfter, COOLDOWN_AFTER_403_MS));
    }

    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
    }

    return resp;
  }
  throw new RateLimitError(COOLDOWN_AFTER_403_MS);
}

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

class RateLimitError extends Error {
  retryAfterMs: number;
  constructor(retryAfterMs: number) {
    super(`Rate limited, retry after ${retryAfterMs}ms`);
    this.retryAfterMs = retryAfterMs;
  }
}

// ── API clients ─────────────────────────────────────────────────────────────

const LCSC_DETAIL_URL = "https://wmsc.lcsc.com/ftps/wm/product/detail";
const JLCPCB_SEARCH_URL =
  "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList";

const HEADERS: Record<string, string> = {
  "User-Agent":
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36",
  Accept: "application/json",
  "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.7",
};

// ── Cache ───────────────────────────────────────────────────────────────────

const cache = new Map<string, { ts: number; data: unknown }>();
const CACHE_TTL_MS = 3600_000;

function getCached<T>(key: string): T | null {
  const entry = cache.get(key);
  if (!entry) return null;
  if (Date.now() - entry.ts > CACHE_TTL_MS) {
    cache.delete(key);
    return null;
  }
  return entry.data as T;
}

function setCache(key: string, data: unknown) {
  cache.set(key, { ts: Date.now(), data });
}

// ── Search ──────────────────────────────────────────────────────────────────

interface JlcpcbProduct {
  componentId: number;
  componentCode: string;
  componentNameEn: string;
  componentModelEn: string;
  componentBrandEn: string;
  componentTypeEn: string;
  stockCount: number;
  componentLibraryType: string;
  componentPrices: { startNumber: number; productPrice: number }[];
  dataManualUrl: string;
  dataManualOfficialLink: string;
  lcscGoodsUrl: string;
  componentSpecificationEn: string;
  describe: string;
  rohsFlag: boolean;
  minPurchaseNum: number;
}

interface NormalizedProduct {
  c_number: string;
  name: string;
  model: string;
  brand: string;
  category: string;
  stock: number;
  is_basic: boolean;
  price_str: string;
  datasheet_url: string;
  lcsc_url: string;
}

function extractCNumber(url: string): string {
  const m = url.match(/C\d+/);
  return m ? m[0] : "";
}

function formatJlcpcbPrices(
  prices: { startNumber: number; productPrice: number }[]
): string {
  if (!prices.length) return "暂无报价";
  return prices
    .slice(0, 4)
    .map((t) => `${t.startNumber}+: $${t.productPrice}`)
    .join(" | ");
}

function normalizeJlcpcbProduct(p: JlcpcbProduct): NormalizedProduct {
  const cNumber = p.componentCode || extractCNumber(p.lcscGoodsUrl || "");
  return {
    c_number: cNumber,
    name: p.componentNameEn || "",
    model: p.componentModelEn || "",
    brand: p.componentBrandEn || "",
    category: p.componentTypeEn || "",
    stock: p.stockCount ?? 0,
    is_basic: p.componentLibraryType === "base",
    price_str: formatJlcpcbPrices(p.componentPrices || []),
    datasheet_url: p.dataManualUrl || p.dataManualOfficialLink || "",
    lcsc_url: p.lcscGoodsUrl || "",
  };
}

async function searchComponents(
  keyword: string,
  page: number,
  pageSize: number
): Promise<{ total: number; products: NormalizedProduct[] }> {
  const cacheKey = `search:${keyword}:${page}:${pageSize}`;
  const cached = getCached<{ total: number; products: NormalizedProduct[] }>(
    cacheKey
  );
  if (cached) return cached;

  const resp = await rateLimitedFetch(JLCPCB_SEARCH_URL, {
    method: "POST",
    headers: {
      ...HEADERS,
      Origin: "https://jlcpcb.com",
      Referer: "https://jlcpcb.com/parts",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ keyword, pageSize, currentPage: page }),
  });

  const raw = (await resp.json()) as {
    data?: {
      componentPageInfo?: { total?: number; list?: JlcpcbProduct[] };
    };
  };

  const pageInfo = raw.data?.componentPageInfo;
  const products = (pageInfo?.list ?? []).map(normalizeJlcpcbProduct);
  const result = { total: pageInfo?.total ?? 0, products };
  setCache(cacheKey, result);
  return result;
}

// ── Detail ──────────────────────────────────────────────────────────────────

interface LcscDetail {
  productCode: string;
  productNameEn: string;
  productModel: string;
  brandNameEn: string;
  catalogName: string;
  stockNumber: number;
  minPacketNumber: number;
  productPriceList: {
    ladder: number;
    productPrice: string;
    currencySymbol: string;
  }[];
  pdfUrl: string;
  productDescEn: string;
  productIntroEn: string;
  isEnvironment: boolean;
  productWeight: string;
  paramVOList: { paramNameEn: string; paramValue: string }[];
}

interface NormalizedDetail {
  c_number: string;
  name: string;
  model: string;
  brand: string;
  category: string;
  stock: number;
  min_order: number;
  price_str: string;
  datasheet_url: string;
  description: string;
  rohs: boolean;
  weight: string;
  params: string[];
}

function formatLcscPrices(
  prices: { ladder: number; productPrice: string; currencySymbol: string }[]
): string {
  if (!prices.length) return "暂无报价";
  return prices
    .slice(0, 4)
    .map((t) => `${t.ladder}+: ${t.currencySymbol || "$"}${t.productPrice}`)
    .join(" | ");
}

async function getProductDetail(
  productCode: string
): Promise<NormalizedDetail | null> {
  const cacheKey = `detail:${productCode}`;
  const cached = getCached<NormalizedDetail>(cacheKey);
  if (cached) return cached;

  const url = new URL(LCSC_DETAIL_URL);
  url.searchParams.set("productCode", productCode);

  const resp = await rateLimitedFetch(url.toString(), { headers: HEADERS });
  const raw = (await resp.json()) as { result?: LcscDetail };
  const r = raw.result;
  if (!r) return null;

  const params = (r.paramVOList ?? [])
    .filter((p) => p.paramNameEn && p.paramValue)
    .map((p) => `  - ${p.paramNameEn}: ${p.paramValue}`);

  const result: NormalizedDetail = {
    c_number: r.productCode ?? "",
    name: r.productNameEn ?? "",
    model: r.productModel ?? "",
    brand: r.brandNameEn ?? "",
    category: r.catalogName ?? "",
    stock: r.stockNumber ?? 0,
    min_order: r.minPacketNumber ?? 0,
    price_str: formatLcscPrices(r.productPriceList ?? []),
    datasheet_url: r.pdfUrl ?? "",
    description: r.productDescEn || r.productIntroEn || "",
    rohs: r.isEnvironment ?? false,
    weight: r.productWeight ?? "",
    params,
  };
  setCache(cacheKey, result);
  return result;
}

// ── Formatters ──────────────────────────────────────────────────────────────

function formatSearchResults(data: {
  total: number;
  products: NormalizedProduct[];
}): string {
  if (!data.products.length) return "未找到匹配的元器件。";
  const lines = [
    `共找到 ${data.total} 个结果，当前显示 ${data.products.length} 个：`,
    "",
  ];
  for (const [i, p] of data.products.entries()) {
    const tag = p.is_basic ? " [Basic]" : " [Extended]";
    lines.push(
      `${i + 1}. [${p.c_number}] ${p.name}${tag}`,
      `   型号: ${p.model} | 厂商: ${p.brand} | 分类: ${p.category}`,
      `   库存: ${p.stock} | 价格: ${p.price_str}`
    );
    if (p.datasheet_url) lines.push(`   数据手册: ${p.datasheet_url}`);
  }
  return lines.join("\n");
}

function formatDetail(d: NormalizedDetail): string {
  const lines = [
    `=== ${d.c_number} ===`,
    `名称: ${d.name}`,
    `型号: ${d.model}`,
    `厂商: ${d.brand}`,
    `分类: ${d.category}`,
    `库存: ${d.stock}`,
    `最小起订: ${d.min_order}`,
    `价格: ${d.price_str}`,
    `数据手册: ${d.datasheet_url || "无"}`,
    `描述: ${d.description}`,
  ];
  if (d.params.length) {
    lines.push("", "技术参数:", ...d.params);
  }
  return lines.join("\n");
}

// ── Rate limit error message ────────────────────────────────────────────────

function rateLimitMsg(e: unknown): string {
  if (e instanceof RateLimitError) {
    return `嘉立创 API 请求过于频繁，已被限流。请等待 ${Math.ceil(e.retryAfterMs / 1000)} 秒后重试。`;
  }
  throw e;
}

// ── MCP Server ──────────────────────────────────────────────────────────────

const server = new McpServer({
  name: "lcsc-component-library",
  version: "0.1.0",
});

server.tool(
  "lcsc_search",
  "搜索 LCSC 嘉立创元器件库。输入关键词，返回匹配的元器件列表，包含 C编号、名称、型号、厂商、分类、库存、阶梯价格、Basic(免费贴片)/Extended(额外收费)标识、数据手册链接。适用于所有元器件搜索场景。",
  {
    keyword: z.string().describe('搜索关键词，如 "STM32F103"、"100nF 0402"'),
    page: z.number().int().min(1).default(1).describe("页码，从1开始"),
    page_size: z
      .number()
      .int()
      .min(1)
      .max(50)
      .default(10)
      .describe("每页数量，1-50"),
  },
  async ({ keyword, page, page_size }) => {
    try {
      const data = await searchComponents(keyword, page, page_size);
      return { content: [{ type: "text", text: formatSearchResults(data) }] };
    } catch (e) {
      try {
        return { content: [{ type: "text", text: rateLimitMsg(e) }] };
      } catch {
        return {
          content: [{ type: "text", text: `搜索失败: ${String(e)}` }],
          isError: true,
        };
      }
    }
  }
);

server.tool(
  "lcsc_detail",
  '根据 LCSC C 编号获取元器件详细信息。返回完整技术参数、阶梯价格、库存、数据手册链接。C编号格式为 "C" + 数字。',
  {
    product_code: z
      .string()
      .describe('LCSC C编号，如 "C123456"'),
  },
  async ({ product_code }) => {
    let code = product_code.trim().toUpperCase();
    if (!code.startsWith("C")) code = "C" + code;
    try {
      const detail = await getProductDetail(code);
      if (!detail)
        return {
          content: [{ type: "text", text: "未找到该元器件的详细信息。" }],
        };
      return { content: [{ type: "text", text: formatDetail(detail) }] };
    } catch (e) {
      try {
        return { content: [{ type: "text", text: rateLimitMsg(e) }] };
      } catch {
        return {
          content: [{ type: "text", text: `查询失败: ${String(e)}` }],
          isError: true,
        };
      }
    }
  }
);

server.tool(
  "lcsc_datasheet",
  "根据 LCSC C 编号获取元器件数据手册(PDF)下载链接。",
  {
    product_code: z
      .string()
      .describe('LCSC C编号，如 "C123456"'),
  },
  async ({ product_code }) => {
    let code = product_code.trim().toUpperCase();
    if (!code.startsWith("C")) code = "C" + code;
    try {
      const detail = await getProductDetail(code);
      const url = detail?.datasheet_url;
      return {
        content: [
          {
            type: "text" as const,
            text: url
              ? `数据手册下载链接: ${url}`
              : "该元器件暂无数据手册链接。",
          },
        ],
      };
    } catch (e) {
      try {
        return { content: [{ type: "text", text: rateLimitMsg(e) }] };
      } catch {
        return {
          content: [{ type: "text", text: `查询失败: ${String(e)}` }],
          isError: true,
        };
      }
    }
  }
);

// ── Main ────────────────────────────────────────────────────────────────────

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("[lcsc-mcp] Server started via stdio");
}

main().catch((e) => {
  console.error("[lcsc-mcp] Fatal:", e);
  process.exit(1);
});
