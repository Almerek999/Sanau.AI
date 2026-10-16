import json
from typing import Dict, Any
from .base import BaseConnector, ConnectorResult
from database.db import get_connection

class SqlDatabaseConnector(BaseConnector):
    def __init__(self, db_alias: str = "Локальная БД (SQLite/Postgres)", enabled: bool = True):
        super().__init__(name="SQL Database Sync", enabled=enabled)
        self.db_alias = db_alias

    def test_connection(self) -> ConnectorResult:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM products")
            count = cursor.fetchone()[0]
            conn.close()
            return ConnectorResult(
                connector_name=self.name,
                target=self.db_alias,
                success=True,
                status_code=200,
                message=f"Подключение активно. База доступна, в каталоге {count} товаров.",
                raw_response={"products_count": count}
            )
        except Exception as e:
            return ConnectorResult(
                connector_name=self.name,
                target=self.db_alias,
                success=False,
                status_code=500,
                message=f"Ошибка соединения с БД: {str(e)}"
            )

    def sync_invoice(self, invoice_data: Dict[str, Any]) -> ConnectorResult:
        if not self.enabled:
            return ConnectorResult(
                connector_name=self.name,
                target=self.db_alias,
                success=False,
                message="Коннектор SQL отключен"
            )

        try:
            conn = get_connection()
            cursor = conn.cursor()

            # 1. Запись шапки накладной
            cursor.execute("""
            INSERT INTO invoices (invoice_number, supplier_name, date, total_amount, status, source_type, raw_data)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                invoice_data.get("invoice_number", "б/н"),
                invoice_data.get("supplier_name", "Не указан"),
                invoice_data.get("date"),
                invoice_data.get("total_amount", 0.0),
                "processed",
                invoice_data.get("source_type", "photo"),
                json.dumps(invoice_data, ensure_ascii=False)
            ))
            invoice_id = cursor.lastrowid

            # 2. Запись строк накладной и обновление актуальной цены закупа в каталоге
            items = invoice_data.get("items", [])
            for it in items:
                cursor.execute("""
                INSERT INTO invoice_items (
                    invoice_id, product_name, quantity, unit, purchase_price,
                    previous_price, price_change_pct, is_price_increase, total_price
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    invoice_id,
                    it.get("product_name"),
                    it.get("quantity", 1),
                    it.get("unit", "шт"),
                    it.get("purchase_price", 0.0),
                    it.get("previous_price"),
                    it.get("price_change_pct", 0.0),
                    1 if it.get("is_price_increase") else 0,
                    it.get("total_price", 0.0)
                ))

                # Обновляем или добавляем товар в каталог
                cursor.execute("""
                INSERT INTO products (name, category, unit, current_purchase_price, recommended_retail_price, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(name) DO UPDATE SET
                    current_purchase_price = excluded.current_purchase_price,
                    recommended_retail_price = excluded.recommended_retail_price,
                    updated_at = CURRENT_TIMESTAMP
                """, (
                    it.get("product_name"),
                    it.get("category", "Общее"),
                    it.get("unit", "шт"),
                    it.get("purchase_price", 0.0),
                    it.get("recommended_retail_price", it.get("purchase_price", 0.0) * 1.25)
                ))

            conn.commit()
            conn.close()

            return ConnectorResult(
                connector_name=self.name,
                target=self.db_alias,
                success=True,
                status_code=200,
                message=f"Транзакция зафиксирована: накладная #{invoice_id} и {len(items)} позиций записаны в SQL",
                records_synced=len(items),
                raw_response={"invoice_id": invoice_id}
            )
        except Exception as e:
            return ConnectorResult(
                connector_name=self.name,
                target=self.db_alias,
                success=False,
                status_code=500,
                message=f"Ошибка транзакции SQL: {str(e)}"
            )
