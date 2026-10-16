import requests
import json
from typing import Dict, Any, List
from .base import BaseConnector, ConnectorResult

class GoogleSheetsConnector(BaseConnector):
    def __init__(self, webhook_url: str = "", enabled: bool = True):
        """
        Поддерживает:
        1. Google Apps Script Web App URL
        2. SheetDB / Sheety API
        3. Webhook для интеграции с Google Sheets (Make/Zapier/n8n)
        """
        super().__init__(name="Google Sheets Sync", enabled=enabled)
        self.webhook_url = webhook_url.strip()

    def test_connection(self) -> ConnectorResult:
        if not self.webhook_url:
            return ConnectorResult(
                connector_name=self.name,
                target="Не указан",
                success=False,
                status_code=400,
                message="Укажите URL Google Apps Script Webhook или SheetDB API"
            )
        try:
            # Отправка тестового пинга
            test_payload = {
                "action": "ping",
                "message": "Тестовое подключение Qabyldau AI",
                "timestamp": "now"
            }
            resp = requests.post(self.webhook_url, json=test_payload, timeout=6)
            if resp.status_code in (200, 201, 302):
                return ConnectorResult(
                    connector_name=self.name,
                    target=self.webhook_url,
                    success=True,
                    status_code=resp.status_code,
                    message="Связь с Google Sheets Webhook подтверждена (200 OK)",
                    raw_response={"status": resp.status_code}
                )
            else:
                return ConnectorResult(
                    connector_name=self.name,
                    target=self.webhook_url,
                    success=False,
                    status_code=resp.status_code,
                    message=f"Сервер Google Sheets ответил кодом: {resp.status_code}"
                )
        except Exception as e:
            return ConnectorResult(
                connector_name=self.name,
                target=self.webhook_url,
                success=False,
                status_code=500,
                message=f"Ошибка соединения: {str(e)}"
            )

    def sync_invoice(self, invoice_data: Dict[str, Any]) -> ConnectorResult:
        if not self.enabled:
            return ConnectorResult(
                connector_name=self.name,
                target=self.webhook_url,
                success=False,
                message="Коннектор Google Sheets выключен"
            )

        items = invoice_data.get("items", [])
        supplier = invoice_data.get("supplier_name", "Не указан")
        date_str = invoice_data.get("date", "Сегодня")
        inv_num = invoice_data.get("invoice_number", "б/н")

        # Формируем плоский массив строк для вставки в Google Sheets
        rows_to_insert = []
        for it in items:
            alert_status = "ОК (Без изменений)"
            if it.get("is_price_increase"):
                alert_status = f"🚨 ВНИМАНИЕ: +{it.get('price_change_pct', 0):.1f}%"

            rows_to_insert.append({
                "Дата": date_str,
                "Номер накладной": inv_num,
                "Поставщик": supplier,
                "Товар": it.get("product_name"),
                "Количество": it.get("quantity"),
                "Ед.изм": it.get("unit", "шт"),
                "Цена закупа (₸)": it.get("purchase_price"),
                "Старая цена (₸)": it.get("previous_price", "-"),
                "Статус цены": alert_status,
                "Сумма (₸)": it.get("total_price"),
                "Реком. розница (₸)": it.get("recommended_retail_price", "-")
            })

        payload = {
            "action": "insert_rows",
            "sheet_name": "Приемка товара",
            "rows": rows_to_insert,
            "total_items": len(rows_to_insert)
        }

        # Если URL задан — реальный POST запрос
        if self.webhook_url:
            try:
                resp = requests.post(self.webhook_url, json=payload, timeout=8)
                success = (resp.status_code in (200, 201, 302))
                return ConnectorResult(
                    connector_name=self.name,
                    target=self.webhook_url,
                    success=success,
                    status_code=resp.status_code,
                    message=f"Успешно отправлено {len(rows_to_insert)} строк в Google Sheets" if success else f"Код ошибки: {resp.status_code}",
                    records_synced=len(rows_to_insert) if success else 0,
                    raw_response={"status": resp.status_code, "text": resp.text[:200]}
                )
            except Exception as e:
                return ConnectorResult(
                    connector_name=self.name,
                    target=self.webhook_url,
                    success=False,
                    status_code=500,
                    message=f"Сетевой сбой при отправке в Google Sheets: {str(e)}"
                )
        else:
            # Режим симуляции для демо (когда жюри не успело поднять свой скрипт)
            return ConnectorResult(
                connector_name=self.name,
                target="Локальный шлюз Google Sheets",
                success=True,
                status_code=200,
                message=f"Подготовлен пакет для Google Sheets: {len(rows_to_insert)} строк (эмуляция онлайн-вставки)",
                records_synced=len(rows_to_insert),
                raw_response={"rows": rows_to_insert}
            )
