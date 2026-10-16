from typing import List, Dict, Any
from .base import BaseConnector, ConnectorResult
from .google_sheets import GoogleSheetsConnector
from .telegram_notifier import TelegramConnector
from .webhook_connector import WebhookConnector
from .sql_connector import SqlDatabaseConnector
from database.db import get_connection, get_all_settings
import config

class IntegrationManager:
    def __init__(self, override_config: Dict[str, Any] = None):
        # 1. Считываем сохраненные настройки из базы данных
        db_settings = get_all_settings()
        
        # 2. Формируем итоговую конфигурацию
        cfg = {
            "sql_enabled": True,
            "google_enabled": db_settings.get("google_enabled", "true").lower() in ("true", "1"),
            "google_sheets_url": db_settings.get("google_sheets_url", ""),
            "telegram_enabled": db_settings.get("telegram_enabled", "true").lower() in ("true", "1"),
            "telegram_token": db_settings.get("telegram_token", config.TELEGRAM_BOT_TOKEN),
            "telegram_chat_id": db_settings.get("telegram_chat_id", config.TELEGRAM_DEFAULT_CHAT_ID),
            "webhook_enabled": db_settings.get("webhook_enabled", "true").lower() in ("true", "1"),
            "webhook_url": db_settings.get("webhook_url", config.DEFAULT_WEBHOOK_URL or "https://webhook.site/demo-sanau"),
            "webhook_auth": db_settings.get("webhook_auth", "")
        }
        
        # Применяем переопределения, если переданы
        if override_config:
            cfg.update(override_config)
            
        self.config = cfg
        
        # Инициализируем коннекторы с текущими настройками
        self.sql_conn = SqlDatabaseConnector(
            enabled=cfg.get("sql_enabled", True)
        )
        self.google_conn = GoogleSheetsConnector(
            webhook_url=cfg.get("google_sheets_url", ""),
            enabled=cfg.get("google_enabled", True)
        )
        self.tg_conn = TelegramConnector(
            bot_token=cfg.get("telegram_token", ""),
            chat_id=cfg.get("telegram_chat_id", ""),
            enabled=cfg.get("telegram_enabled", True)
        )
        self.webhook_conn = WebhookConnector(
            endpoint_url=cfg.get("webhook_url", ""),
            auth_header=cfg.get("webhook_auth", ""),
            enabled=cfg.get("webhook_enabled", True)
        )

    def get_all_connectors(self) -> List[BaseConnector]:
        return [self.sql_conn, self.google_conn, self.tg_conn, self.webhook_conn]

    def test_all(self) -> List[ConnectorResult]:
        return [conn.test_connection() for conn in self.get_all_connectors()]

    def sync_to_all(self, invoice_data: Dict[str, Any]) -> List[ConnectorResult]:
        """Параллельная или последовательная отправка во все включенные сервисы"""
        results = []
        for conn in self.get_all_connectors():
            if conn.enabled:
                res = conn.sync_invoice(invoice_data)
                results.append(res)
                self._log_sync(res)
        return results

    def _log_sync(self, res: ConnectorResult):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO sync_logs (service_name, target_destination, status, items_count, response_message)
            VALUES (?, ?, ?, ?, ?)
            """, (
                res.connector_name,
                res.target,
                "SUCCESS" if res.success else "FAILED",
                res.records_synced,
                res.message
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Log sync error: {e}")

    @staticmethod
    def get_recent_logs(limit: int = 15):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
            SELECT service_name, target_destination, status, items_count, response_message, created_at
            FROM sync_logs
            ORDER BY id DESC LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception:
            return []
