import requests
import time
from typing import Dict, Any
from .base import BaseConnector, ConnectorResult

class WebhookConnector(BaseConnector):
    def __init__(self, endpoint_url: str = "", auth_header: str = "", enabled: bool = True):
        super().__init__(name="1C / ERP Webhook API", enabled=enabled)
        self.endpoint_url = endpoint_url.strip()
        self.auth_header = auth_header.strip()

    def test_connection(self) -> ConnectorResult:
        if not self.endpoint_url:
            return ConnectorResult(
                connector_name=self.name,
                target="Не указан",
                success=False,
                status_code=400,
                message="Укажите URL эндпоинта (например, https://webhook.site/ или 1C REST API)"
            )
        try:
            headers = {"Content-Type": "application/json"}
            if self.auth_header:
                headers["Authorization"] = self.auth_header

            start_t = time.time()
            resp = requests.post(
                self.endpoint_url,
                json={"event": "ping", "system": "Sanau.AI", "status": "active"},
                headers=headers,
                timeout=5
            )
            elapsed_ms = int((time.time() - start_t) * 1000)
            return ConnectorResult(
                connector_name=self.name,
                target=self.endpoint_url,
                success=(200 <= resp.status_code < 300),
                status_code=resp.status_code,
                message=f"Эндпоинт ответил за {elapsed_ms}ms со статусом {resp.status_code}",
                raw_response={"status_code": resp.status_code}
            )
        except Exception as e:
            return ConnectorResult(
                connector_name=self.name,
                target=self.endpoint_url,
                success=False,
                status_code=500,
                message=f"Ошибка соединения с вебхуком: {str(e)}"
            )

    def sync_invoice(self, invoice_data: Dict[str, Any]) -> ConnectorResult:
        if not self.enabled:
            return ConnectorResult(
                connector_name=self.name,
                target=self.endpoint_url,
                success=False,
                message="Коннектор 1C/ERP Webhook отключен"
            )

        if not self.endpoint_url:
            return ConnectorResult(
                connector_name=self.name,
                target="Локальный шлюз ERP",
                success=True,
                status_code=200,
                message="Эмуляция ERP Webhook: JSON-структура 1C сформирована успешно (URL не задан)",
                records_synced=len(invoice_data.get("items", [])),
                raw_response=invoice_data
            )

        # Стандартизированный ERP / 1C REST Payload
        payload = {
            "source": "Sanau.AI",
            "document_type": "ПриходнаяНакладная",
            "invoice_number": invoice_data.get("invoice_number", "б/н"),
            "date": invoice_data.get("date"),
            "supplier": {
                "name": invoice_data.get("supplier_name"),
                "city": "Тараз"
            },
            "financials": {
                "total_sum_kzt": invoice_data.get("total_amount", 0),
                "currency": "KZT",
                "price_spike_detected": any(it.get("is_price_increase") for it in invoice_data.get("items", []))
            },
            "inventory_lines": [
                {
                    "sku_name": it.get("product_name"),
                    "qty": it.get("quantity"),
                    "uom": it.get("unit", "шт"),
                    "cost_price": it.get("purchase_price"),
                    "previous_cost_price": it.get("previous_price"),
                    "price_delta_pct": it.get("price_change_pct", 0),
                    "recommended_retail": it.get("recommended_retail_price"),
                    "line_total": it.get("total_price")
                }
                for it in invoice_data.get("items", [])
            ]
        }

        try:
            headers = {"Content-Type": "application/json"}
            if self.auth_header:
                headers["Authorization"] = self.auth_header

            start_t = time.time()
            resp = requests.post(self.endpoint_url, json=payload, headers=headers, timeout=8)
            elapsed_ms = int((time.time() - start_t) * 1000)
            success = (200 <= resp.status_code < 300)

            return ConnectorResult(
                connector_name=self.name,
                target=self.endpoint_url,
                success=success,
                status_code=resp.status_code,
                message=f"Пакет 1C/ERP доставлен ({elapsed_ms}ms, HTTP {resp.status_code})" if success else f"HTTP {resp.status_code}: {resp.text[:100]}",
                records_synced=len(payload["inventory_lines"]) if success else 0,
                raw_response={"status_code": resp.status_code, "payload": payload}
            )
        except Exception as e:
            return ConnectorResult(
                connector_name=self.name,
                target=self.endpoint_url,
                success=False,
                status_code=500,
                message=f"Ошибка передачи в ERP: {str(e)}"
            )
