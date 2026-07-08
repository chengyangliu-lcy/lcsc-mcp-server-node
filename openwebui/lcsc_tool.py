import re
import time
from typing import Any, Dict, List, Optional

import requests
from pydantic import Field
from pydantic.fields import FieldInfo


class Tools:
    def __init__(self):
        self.SEARCH_URL = "https://so.szlcsc.com/global.html"
        self.ITEM_BASE_URL = "https://item.szlcsc.com"
        self.JLCPCB_SEARCH_URL = (
            "https://jlcpcb.com/api/overseas-pcb-order/v1/"
            "shoppingCart/smtGood/selectSmtComponentList"
        )
        self.LCSC_DETAIL_URL = "https://wmsc.lcsc.com/ftps/wm/product/detail"
        self.HEADERS = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0 Safari/537.36"
            ),
            "Accept": "application/json",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.7",
        }
        self.last_request_time = 0.0
        self.cooldown_until = 0.0
        self.min_interval_seconds = 3.0
        self.cooldown_after_403_seconds = 30.0
        self.max_retries = 2

    def _sleep_for_rate_limit(self):
        """
        Do not use this tool
        """
        now = time.time()
        if self.cooldown_until > now:
            time.sleep(self.cooldown_until - now)

        since_last = time.time() - self.last_request_time
        if since_last < self.min_interval_seconds:
            time.sleep(self.min_interval_seconds - since_last)

        self.last_request_time = time.time()

    def _request_search_page(self, keyword: str, page: int) -> str:
        """
        Do not use this tool
        """
        raise RuntimeError("旧版立创商城页面解析已停用，请使用 JSON API 查询。")

    def _request_json(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """
        Do not use this tool
        """
        for attempt in range(self.max_retries + 1):
            self._sleep_for_rate_limit()
            response = requests.request(method, url, timeout=60, **kwargs)

            if response.status_code in (403, 429):
                self.cooldown_until = time.time() + self.cooldown_after_403_seconds
                if attempt < self.max_retries:
                    time.sleep(10 * (2**attempt))
                    continue
                raise RuntimeError("立创/JLCPCB API 请求过于频繁，请稍后重试。")

            response.raise_for_status()
            try:
                data = response.json()
            except ValueError as exc:
                raise RuntimeError(
                    "立创/JLCPCB API 返回的不是有效 JSON，可能触发风控或接口结构变化。"
                ) from exc

            if not isinstance(data, dict):
                raise RuntimeError("立创/JLCPCB API 返回结构异常。")
            return data

        raise RuntimeError("请求失败，请稍后重试。")

    def _coerce_int(self, value: Any, default: int, minimum: int, maximum: int) -> int:
        """
        Do not use this tool
        """
        if isinstance(value, FieldInfo) or value is None:
            return default
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return default
        return min(maximum, max(minimum, parsed))

    def _strip_html(self, value: Any) -> str:
        """
        Do not use this tool
        """
        if value is None:
            return ""
        text = str(value)
        text = re.sub(r"<[^>]*>", "", text)
        return (
            text.replace("&nbsp;", " ")
            .replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", '"')
            .strip()
        )

    def _get_string(self, item: Dict[str, Any], *keys: str) -> str:
        """
        Do not use this tool
        """
        for key in keys:
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                return self._strip_html(value)
            if isinstance(value, (int, float)):
                return str(value)
        return ""

    def _get_number(self, item: Dict[str, Any], *keys: str) -> int:
        """
        Do not use this tool
        """
        for key in keys:
            value = item.get(key)
            if isinstance(value, int):
                return value
            if isinstance(value, str) and value.strip():
                try:
                    return int(float(value.replace(",", "")))
                except ValueError:
                    pass
        return 0

    def _normalize_product_code(self, product_code: str) -> str:
        """
        Do not use this tool
        """
        code = product_code.strip().upper()
        if not re.fullmatch(r"C?\d+", code):
            raise RuntimeError(
                "立创 C 编号格式不正确，请输入类似 C8734 或 8734 的编号。"
            )
        return code if code.startswith("C") else f"C{code}"

    def _format_prices(self, prices: List[Dict[str, Any]]) -> str:
        """
        Do not use this tool
        """
        formatted = []
        for item in prices[:5]:
            ladder = self._get_string(
                item, "startPurchasedNumber", "startNumber", "ladder", "qty"
            )
            price = self._get_string(item, "productPrice", "price", "unitPrice")
            symbol = self._get_string(item, "currencySymbol") or "¥"
            if ladder and price:
                formatted.append(f"{ladder}+: {symbol}{price}")
        return " | ".join(formatted) if formatted else "暂无报价"

    def _format_jlcpcb_prices(self, prices: List[Dict[str, Any]]) -> str:
        """
        Do not use this tool
        """
        formatted = []
        for item in prices[:5]:
            ladder = self._get_string(item, "startNumber", "startPurchasedNumber")
            price = self._get_string(item, "productPrice", "price", "unitPrice")
            if ladder and price:
                formatted.append(f"{ladder}+: ¥{price}")
        return " | ".join(formatted) if formatted else "暂无报价"

    def _normalize_jlcpcb_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Do not use this tool
        """
        prices = item.get("componentPrices") or []
        if not isinstance(prices, list):
            prices = []

        datasheet_url = self._get_string(
            item, "dataManualUrl", "dataManualOfficialLink"
        )
        library_type = self._get_string(item, "componentLibraryType").lower()
        library_label = "Basic" if library_type == "base" else "Extended"

        return {
            "c_number": self._get_string(item, "componentCode"),
            "name": self._get_string(item, "componentNameEn", "componentName"),
            "model": self._get_string(item, "componentModelEn", "componentModel"),
            "brand": self._get_string(item, "componentBrandEn", "componentBrand"),
            "category": self._get_string(item, "componentTypeEn", "componentType"),
            "stock": self._get_number(item, "stockCount"),
            "price": self._format_jlcpcb_prices(
                [p for p in prices if isinstance(p, dict)]
            ),
            "datasheet_url": datasheet_url,
            "datasheet_source": "english" if datasheet_url else "",
            "detail_url": self._get_string(item, "lcscGoodsUrl"),
            "library_label": library_label,
        }

    def _search_records(
        self, keyword: str, page: int, page_size: int
    ) -> Dict[str, Any]:
        """
        Do not use this tool
        """
        payload = {
            "keyword": keyword.strip(),
            "pageSize": min(max(page_size, 1), 50),
            "currentPage": max(page, 1),
        }
        headers = {
            **self.HEADERS,
            "Content-Type": "application/json",
            "Origin": "https://jlcpcb.com",
            "Referer": "https://jlcpcb.com/parts",
        }
        data = self._request_json(
            "POST", self.JLCPCB_SEARCH_URL, headers=headers, json=payload
        )
        page_info = data.get("data", {}).get("componentPageInfo", {})
        if not isinstance(page_info, dict):
            page_info = {}
        records = page_info.get("list") or []
        if not isinstance(records, list):
            records = []
        records = [item for item in records if isinstance(item, dict)]
        products = [self._normalize_jlcpcb_item(item) for item in records]
        total = page_info.get("total") or len(products)
        return {"total": int(total), "records": records, "products": products}

    def _get_detail(self, product_code: str) -> Optional[Dict[str, Any]]:
        """
        Do not use this tool
        """
        code = self._normalize_product_code(product_code)
        data = self._request_json(
            "GET",
            self.LCSC_DETAIL_URL,
            headers=self.HEADERS,
            params={"productCode": code},
        )
        result = data.get("result")
        return result if isinstance(result, dict) else None

    def _get_detail_url(self, product_code: str) -> str:
        """
        Do not use this tool
        """
        code = self._normalize_product_code(product_code)
        try:
            result = self._search_records(code, 1, 10)
        except Exception:
            return ""

        for item in result.get("products", []):
            if str(item.get("c_number", "")).upper() == code:
                return str(item.get("detail_url") or "")
        return ""

    def _format_search_results(self, total: int, products: List[Dict[str, Any]]) -> str:
        """
        Do not use this tool
        """
        if not products:
            return "未找到匹配的元器件。"

        lines = [f"共找到 {total} 个结果，当前显示 {len(products)} 个：", ""]
        for index, item in enumerate(products, start=1):
            label = (
                f" [{item.get('library_label')}]" if item.get("library_label") else ""
            )
            lines.extend(
                [
                    f"{index}. [{item.get('c_number')}] {item.get('name')}{label}",
                    (
                        f"   型号: {item.get('model')} | 厂商: {item.get('brand')} "
                        f"| 分类: {item.get('category')}"
                    ),
                    f"   库存: {item.get('stock')} | 价格: {item.get('price')}",
                ]
            )
            if item.get("datasheet_url"):
                lines.append(f"   数据手册: {self._format_datasheet(item)}")
            if item.get("detail_url"):
                lines.append(f"   详情页: {item.get('detail_url')}")
        return "\n".join(lines)

    def _format_datasheet(self, item: Dict[str, Any]) -> str:
        """
        Do not use this tool
        """
        url = item.get("datasheet_url")
        if not url:
            return "无"
        return str(url)

    def _detail_params(self, detail: Dict[str, Any]) -> List[str]:
        """
        Do not use this tool
        """
        raw_params = detail.get("paramVOList") or []
        if not isinstance(raw_params, list):
            return []
        params = []
        for item in raw_params:
            if not isinstance(item, dict):
                continue
            name = self._get_string(item, "paramNameEn", "paramName")
            value = self._get_string(item, "paramValue")
            if name and value:
                params.append(f"  - {name}: {value}")
        return params

    def LCSCSearch(
        self,
        keyword: str = Field(
            ..., description='搜索关键词，例如 "STM32F103"、"100nF 0402"'
        ),
        page: int = Field(1, description="页码，从 1 开始"),
        page_size: int = Field(10, description="每页数量，1-30"),
    ) -> str:
        """
        搜索 JLCPCB/LCSC 元器件，返回 C 编号、名称、型号、厂商、分类、库存、阶梯价格、数据手册和详情页。
        """
        try:
            safe_page = self._coerce_int(page, default=1, minimum=1, maximum=9999)
            safe_page_size = self._coerce_int(
                page_size, default=10, minimum=1, maximum=30
            )
            result = self._search_records(keyword, safe_page, safe_page_size)
            return self._format_search_results(result["total"], result["products"])
        except requests.exceptions.Timeout:
            return "Error: 请求 JLCPCB 搜索接口超时。"
        except requests.exceptions.ConnectionError:
            return "Error: 无法连接 JLCPCB 搜索接口。"
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else "unknown"
            return f"HTTP error from JLCPCB/LCSC API: {status_code}"
        except Exception as e:
            return f"Unexpected error: {str(e)}"

    def LCSCDetail(
        self,
        product_code: str = Field(
            ..., description='立创商城 C 编号，例如 "C8734"；也可以只输入数字'
        ),
    ) -> str:
        """
        根据立创商城 C 编号查询元器件详情、库存、价格、技术参数和数据手册链接。
        """
        try:
            detail = self._get_detail(product_code)
            if not detail:
                return "未找到该元器件的详细信息。"

            prices = detail.get("productPriceList") or []
            if not isinstance(prices, list):
                prices = []
            params = self._detail_params(detail)
            code = self._get_string(detail, "productCode")
            detail_url = self._get_detail_url(code) if code else ""
            description = self._get_string(
                detail, "productDescEn", "productIntroEn", "productDesc"
            )
            lines = [
                f"=== {code} ===",
                f"名称: {self._get_string(detail, 'productNameEn', 'productName')}",
                f"型号: {self._get_string(detail, 'productModel')}",
                f"厂商: {self._get_string(detail, 'brandNameEn', 'brandName')}",
                f"分类: {self._get_string(detail, 'catalogName')}",
                f"库存: {self._get_number(detail, 'stockNumber')}",
                f"最小起订: {self._get_number(detail, 'minPacketNumber', 'minBuyNumber') or '未知'}",
                f"价格: {self._format_prices([p for p in prices if isinstance(p, dict)])}",
                f"数据手册: {self._format_datasheet({'datasheet_url': self._get_string(detail, 'pdfUrl')})}",
                f"详情页: {detail_url or '无'}",
                f"描述: {description}",
            ]
            if params:
                lines.extend(["", "技术参数:", *params])
            return "\n".join(lines)
        except Exception as e:
            return f"Unexpected error: {str(e)}"

    def LCSCDatasheet(
        self,
        product_code: str = Field(
            ..., description='立创商城 C 编号，例如 "C8734"；也可以只输入数字'
        ),
    ) -> str:
        """
        根据立创商城 C 编号获取元器件数据手册 PDF 链接。
        """
        try:
            detail = self._get_detail(product_code)
            if not detail:
                return "未找到该元器件。"
            url = self._get_string(detail, "pdfUrl")
            if not url:
                return "该元器件暂无数据手册链接。"
            return f"数据手册下载链接: {url}"
        except Exception as e:
            return f"Unexpected error: {str(e)}"
