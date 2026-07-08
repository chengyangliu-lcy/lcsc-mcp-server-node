import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "openwebui" / "lcsc_tool.py"


def load_module():
    spec = importlib.util.spec_from_file_location("openwebui_lcsc_tool", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class OpenWebuiLcscToolTests(unittest.TestCase):
    def test_search_uses_jlcpcb_json_api_and_formats_results(self):
        module = load_module()
        tool = module.Tools()
        calls = []

        def fake_request_json(method, url, **kwargs):
            calls.append((method, url, kwargs))
            return {
                "data": {
                    "componentPageInfo": {
                        "total": 1,
                        "list": [
                            {
                                "componentCode": "C8734",
                                "componentNameEn": "MCU",
                                "componentModelEn": "STM32F103C8T6",
                                "componentBrandEn": "ST",
                                "componentTypeEn": "Microcontrollers",
                                "stockCount": 123,
                                "componentLibraryType": "base",
                                "componentPrices": [
                                    {"startNumber": 1, "productPrice": 1.23}
                                ],
                                "dataManualUrl": "https://example.com/stm32.pdf",
                                "lcscGoodsUrl": "https://item.szlcsc.com/8734.html",
                            }
                        ],
                    }
                }
            }

        def fail_if_old_page_is_used(*args, **kwargs):
            raise AssertionError("old szlcsc search page should not be requested")

        tool._request_json = fake_request_json
        tool._request_search_page = fail_if_old_page_is_used

        output = tool.LCSCSearch("STM32F103", page=1, page_size=5)

        self.assertEqual(calls[0][0], "POST")
        self.assertEqual(calls[0][1], tool.JLCPCB_SEARCH_URL)
        self.assertEqual(
            calls[0][2]["json"],
            {"keyword": "STM32F103", "pageSize": 5, "currentPage": 1},
        )
        self.assertIn("共找到 1 个结果", output)
        self.assertIn("[C8734] MCU [Basic]", output)
        self.assertIn(
            "型号: STM32F103C8T6 | 厂商: ST | 分类: Microcontrollers", output
        )
        self.assertIn("库存: 123 | 价格: 1+: ¥1.23", output)
        self.assertIn("数据手册: https://example.com/stm32.pdf", output)

    def test_detail_uses_lcsc_json_detail_api(self):
        module = load_module()
        tool = module.Tools()
        calls = []

        def fake_request_json(method, url, **kwargs):
            calls.append((method, url, kwargs))
            if url == tool.JLCPCB_SEARCH_URL:
                return {
                    "data": {
                        "componentPageInfo": {
                            "total": 1,
                            "list": [
                                {
                                    "componentCode": "C8734",
                                    "lcscGoodsUrl": "https://www.lcsc.com/product-detail/st-stm32f103c8t6_C8734.html",
                                }
                            ],
                        }
                    }
                }
            return {
                "result": {
                    "productCode": "C8734",
                    "productNameEn": "MCU",
                    "productModel": "STM32F103C8T6",
                    "brandNameEn": "ST",
                    "catalogName": "Microcontrollers",
                    "stockNumber": 123,
                    "minPacketNumber": 1,
                    "productPriceList": [
                        {
                            "ladder": 1,
                            "productPrice": "1.23",
                            "currencySymbol": "$",
                        }
                    ],
                    "pdfUrl": "https://example.com/stm32.pdf",
                    "productDescEn": "ARM MCU",
                    "paramVOList": [
                        {"paramNameEn": "Core", "paramValue": "ARM Cortex-M3"}
                    ],
                }
            }

        tool._request_json = fake_request_json

        output = tool.LCSCDetail("8734")

        self.assertEqual(calls[0][0], "GET")
        self.assertEqual(calls[0][1], tool.LCSC_DETAIL_URL)
        self.assertEqual(calls[0][2]["params"], {"productCode": "C8734"})
        self.assertEqual(calls[1][0], "POST")
        self.assertEqual(calls[1][1], tool.JLCPCB_SEARCH_URL)
        self.assertIn("=== C8734 ===", output)
        self.assertIn("型号: STM32F103C8T6", output)
        self.assertIn("价格: 1+: $1.23", output)
        self.assertIn(
            "详情页: https://www.lcsc.com/product-detail/st-stm32f103c8t6_C8734.html",
            output,
        )
        self.assertIn("  - Core: ARM Cortex-M3", output)

    def test_datasheet_returns_pdf_from_detail_api(self):
        module = load_module()
        tool = module.Tools()
        tool._request_json = lambda *args, **kwargs: {
            "result": {
                "productCode": "C8734",
                "pdfUrl": "https://example.com/stm32.pdf",
            }
        }

        self.assertEqual(
            tool.LCSCDatasheet("C8734"),
            "数据手册下载链接: https://example.com/stm32.pdf",
        )

    def test_invalid_product_code_returns_clear_error(self):
        module = load_module()
        tool = module.Tools()

        self.assertIn("C 编号格式不正确", tool.LCSCDetail("abc"))
        self.assertIn("C 编号格式不正确", tool.LCSCDatasheet("abc"))


if __name__ == "__main__":
    unittest.main()
