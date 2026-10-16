import requests
from typing import Dict, Any
from .base import BaseConnector, ConnectorResult

class TelegramConnector(BaseConnector):
    def __init__(self, bot_token: str = "", chat_id: str = "", enabled: bool = True):
        super().__init__(name="Telegram Notifier", enabled=enabled)
        self.bot_token = bot_token.strip()
        self.chat_id = chat_id.strip()

    def test_connection(self) -> ConnectorResult:
        if not self.bot_token or not self.chat_id:
            return ConnectorResult(
                connector_name=self.name,
                target=self.chat_id or "Не указан",
                success=False,
                status_code=400,
                message="Не указан Bot Token или Chat ID"
            )
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": "🟢 *Sanau.AI: Тест соединения успешен!*\nСервис готов получать уведомления о поставках и алерты цен.",
                "parse_mode": "Markdown"
            }
            resp = requests.post(url, json=payload, timeout=5)
            if resp.status_code == 200:
                return ConnectorResult(
                    connector_name=self.name,
                    target=f"Chat ID: {self.chat_id}",
                    success=True,
                    status_code=200,
                    message="Успешное тестовое сообщение отправлено в Telegram",
                    raw_response=resp.json()
                )
            else:
                return ConnectorResult(
                    connector_name=self.name,
                    target=f"Chat ID: {self.chat_id}",
                    success=False,
                    status_code=resp.status_code,
                    message=f"Ошибка Telegram API: {resp.text}"
                )
        except Exception as e:
            return ConnectorResult(
                connector_name=self.name,
                target=self.chat_id,
                success=False,
                status_code=500,
                message=f"Исключение при отправке в Telegram: {str(e)}"
            )

    def sync_invoice(self, invoice_data: Dict[str, Any]) -> ConnectorResult:
        if not self.enabled:
            return ConnectorResult(
                connector_name=self.name,
                target=self.chat_id,
                success=False,
                message="Коннектор отключен пользователем"
            )

        if not self.bot_token or not self.chat_id:
            return ConnectorResult(
                connector_name=self.name,
                target="Локальный эмулятор",
                success=True,
                status_code=200,
                message="Эмуляция Telegram: сообщение сформировано успешно (токен не задан)",
                records_synced=len(invoice_data.get("items", []))
            )

        # Формируем красивый текст сообщения
        supplier = invoice_data.get("supplier_name", "Неизвестный поставщик")
        inv_num = invoice_data.get("invoice_number", "б/н")
        total = invoice_data.get("total_amount", 0)
        items = invoice_data.get("items", [])
        price_alerts = [item for item in items if item.get("is_price_increase")]

        text_lines = [
            f"📦 *Sanau.AI: Принята накладная №{inv_num}*",
            f"🏢 *Поставщик:* {supplier}",
            f"💰 *Общая сумма:* {total:,.0f} ₸".replace(",", " "),
            f"📋 *Позиций:* {len(items)}",
            ""
        ]

        if price_alerts:
            text_lines.append("🚨 *ВНИМАНИЕ! ОБНАРУЖЕН РОСТ ЗАКУПОЧНЫХ ЦЕН:*")
            for alert in price_alerts:
                old_p = alert.get("previous_price", 0)
                new_p = alert.get("purchase_price", 0)
                pct = alert.get("price_change_pct", 0)
                rec_retail = alert.get("recommended_retail_price", new_p * 1.25)
                text_lines.append(
                    f"⚠️ *{alert.get('product_name')}*\n"
                    f"   Было: {old_p:.0f} ₸ ➔ Стало: *{new_p:.0f} ₸* (+{pct:.1f}%)\n"
                    f"   👉 Рекомендованная цена розницы: *{rec_retail:.0f} ₸*"
                )
            text_lines.append("")
        else:
            text_lines.append("✅ *Все закупочные цены в пределах нормы.*")

        text_lines.append("📊 _Данные автоматически занесены в систему учета._")
        full_text = "\n".join(text_lines)

        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": full_text,
                "parse_mode": "Markdown"
            }
            resp = requests.post(url, json=payload, timeout=6)
            success = (resp.status_code == 200)
            return ConnectorResult(
                connector_name=self.name,
                target=f"Chat ID: {self.chat_id}",
                success=success,
                status_code=resp.status_code,
                message="Уведомление и финансовый алерт успешно доставлены в Telegram" if success else resp.text,
                records_synced=len(items),
                raw_response=resp.json() if success else {}
            )
        except Exception as e:
            return ConnectorResult(
                connector_name=self.name,
                target=self.chat_id,
                success=False,
                status_code=500,
                message=f"Ошибка соединения с Telegram: {str(e)}"
            )
