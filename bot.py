import os
import time
import json
import base64
import requests
import threading
from typing import Dict, Any, Optional
from database.db import get_setting, set_setting
from services.ai_engine import process_invoice, get_demo_sample_invoice
from services.radar import to_float
from services.connectors.manager import IntegrationManager
import config

cached_invoices: Dict[str, Any] = {}

class TelegramBotWorker:
    def __init__(self):
        self.running = False
        self.thread: Optional[threading.Thread] = None

    def get_token(self) -> str:
        token = get_setting("telegram_token", "").strip()
        if not token:
            token = config.TELEGRAM_BOT_TOKEN.strip()
        return token

    def get_webapp_url(self) -> str:
        url = get_setting("webapp_url", "").strip()
        if not url:
            # Fallback на локальный адрес
            url = "http://localhost:8000"
        return url

    def start(self, force_restart: bool = False):
        if self.running and not force_restart:
            return
        if self.running and force_restart:
            self.running = False
            time.sleep(0.5)

        token = self.get_token()
        if not token:
            print("Telegram Bot: Токен не настроен. Бот ожидает привязки токена в настройках.")
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.thread.start()
        print(f"Telegram Bot Worker запущен с токеном: {token[:10]}...")
        
        # Автоматическая настройка кнопки меню Telegram если есть HTTPS адрес
        url = self.get_webapp_url()
        if url.startswith("https://"):
            try:
                requests.post(f"https://api.telegram.org/bot{token}/setChatMenuButton", json={
                    "menu_button": {"type": "web_app", "text": "📱 Открыть Mini App", "web_app": {"url": url}}
                }, timeout=5)
            except Exception:
                pass

    def stop(self):
        self.running = False

    def _poll_loop(self):
        offset = 0
        while self.running:
            token = self.get_token()
            if not token:
                time.sleep(3)
                continue
                
            url = f"https://api.telegram.org/bot{token}/getUpdates"
            params = {"offset": offset, "timeout": 20}
            try:
                resp = requests.get(url, params=params, timeout=25)
                if resp.status_code == 200:
                    data = resp.json()
                    for update in data.get("result", []):
                        offset = update["update_id"] + 1
                        self._handle_update(token, update)
                else:
                    time.sleep(2)
            except Exception as e:
                time.sleep(3)

    def _make_webapp_button(self, title: str = "📱 Открыть Mini App") -> Dict[str, Any]:
        url = self.get_webapp_url()
        if url.startswith("https://"):
            return {"text": title, "web_app": {"url": url}}
        else:
            return {"text": f"{title} (localhost:8000)", "callback_data": "miniapp_info"}

    def _send_message(self, token: str, chat_id: int, text: str, reply_markup: Optional[Dict] = None):
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        try:
            resp = requests.post(url, json=payload, timeout=8)
            if resp.status_code != 200:
                print(f"⚠️ Telegram API Send Error ({resp.status_code}): {resp.text}")
                # Fallback: пробуем отправить чистым текстом без форматирования и разметки
                fallback_payload = {"chat_id": chat_id, "text": text}
                fb_resp = requests.post(url, json=fallback_payload, timeout=8)
                if fb_resp.status_code == 200:
                    print("✅ Сообщение успешно доставлено через текстовый fallback")
                else:
                    print(f"❌ Fallback также не удался: {fb_resp.status_code} {fb_resp.text}")
        except Exception as e:
            print(f"Error sending TG message: {e}")

    def _handle_update(self, token: str, update: Dict[str, Any]):
        webapp_url = self.get_webapp_url()

        # 1. Обработка нажатий Inline-кнопок (Callback Queries)
        if "callback_query" in update:
            cq = update["callback_query"]
            data = cq.get("data", "")
            chat_id = cq["message"]["chat"]["id"]
            print(f"🔘 Нажата кнопка: {data} от chat_id {chat_id}")
            
            # Подтверждение нажатия кнопки в Telegram
            try:
                requests.post(f"https://api.telegram.org/bot{token}/answerCallbackQuery", json={"callback_query_id": cq["id"]}, timeout=5)
            except Exception:
                pass

            if data == "miniapp_info":
                info_msg = (
                    "🌐 *Панель управления Sanau.AI:*\n\n"
                    "💻 *На компьютере:* откройте в браузере: http://localhost:8000\n\n"
                    "💡 *Для открытия внутри мобильного Telegram как Mini App:*\n"
                    "Telegram требует защищенную HTTPS ссылку. "
                    "Вы можете привязать публичный HTTPS адрес (ngrok / Cloudflare / домен) во вкладке «Сервисы»."
                )
                self._send_message(token, chat_id, info_msg)
                return

            if data == "demo_test":
                inv = process_invoice(sample_id="spike_milk_flour")
                self._send_invoice_report(token, chat_id, inv)
            elif data.startswith("sync_"):
                inv_key = data.replace("sync_", "")
                inv = cached_invoices.get(inv_key) or get_demo_sample_invoice("spike_milk_flour")
                
                # Запускаем отправку по всем сервисам
                manager = IntegrationManager()
                results = manager.sync_to_all(inv)
                
                success_list = [f"✅ {r.connector_name} ({r.records_synced} строк)" for r in results if r.success]
                report = "🚀 *Данные успешно разнесены во все сервисы:*\n\n" + "\n".join(success_list)
                self._send_message(token, chat_id, report)
            elif data == "connect":
                msg = (
                    "⚙️ *Связывание сервисов с Sanau.AI:*\n\n"
                    "1. Откройте панель управления: http://localhost:8000\n"
                    "2. В приложении перейдите во вкладку *«Сервисы»*.\n"
                    "3. Вставьте ссылку на Google Таблицу, 1C Webhook или OpenAI/Gemini API Key.\n"
                    "4. Нажмите *«Тест соединения»* — и данные будут поступать мгновенно!"
                )
                kb = {
                    "inline_keyboard": [
                        [self._make_webapp_button("📱 Открыть Mini App / Панель")]
                    ]
                }
                self._send_message(token, chat_id, msg, reply_markup=kb)
            return

        # 2. Обработка сообщений
        message = update.get("message")
        if not message:
            return

        chat_id = message["chat"]["id"]
        set_setting("telegram_chat_id", str(chat_id))
        msg_text = message.get("text", "")
        print(f"📩 Новое сообщение от {chat_id}: {msg_text or 'медиафайл'}")

        # Команда /start
        if msg_text.startswith("/start"):
            welcome_text = (
                "👋 *Сәлеметсіз бе / Здравствуйте!*\n"
                "Добро пожаловать в *Sanau.AI* — мультимодальный AI-товаровед и радар маржи для предпринимателей г. Тараз и Жамбылской области.\n\n"
                "📦 *Что умеет бот:*\n"
                "• 📸 *Фото накладной:* просто сфотографируйте бумажную накладную и пришлите сюда.\n"
                "• 🎙️ *Голосовое сообщение:* надиктуйте приемку на казахском или русском (например: _«20 сүт Родина 440 теңгеден келді...»_).\n"
                "• 🚨 *Радар маржи:* ИИ мгновенно выявит скрытое подорожание товара и рассчитает новую цену розницы.\n"
                "• 🔌 *Интеграции:* мгновенная запись в Google Sheets, 1C и базу данных магазина.\n\n"
                "💻 *Панель управления:* http://localhost:8000"
            )
            kb = {
                "inline_keyboard": [
                    [self._make_webapp_button("📱 Открыть Sanau.AI Mini App")],
                    [{"text": "⚡ Тест накладной (Демо со сцены)", "callback_data": "demo_test"}],
                    [{"text": "⚙️ Связать мои сервисы (Google/1C)", "callback_data": "connect"}]
                ]
            }
            self._send_message(token, chat_id, welcome_text, reply_markup=kb)
            return

        # Обработка фото накладной
        if "photo" in message:
            self._send_message(token, chat_id, "⏳ *AI Vision обрабатывает фото накладной и сверяет цены с каталогом Тараза...*")
            photos = message["photo"]
            best_photo = photos[-1]
            file_id = best_photo["file_id"]
            
            # Скачиваем фото с серверов Telegram
            try:
                f_resp = requests.get(f"https://api.telegram.org/bot{token}/getFile?file_id={file_id}", timeout=10)
                file_path = f_resp.json()["result"]["file_path"]
                img_bytes = requests.get(f"https://api.telegram.org/file/bot{token}/{file_path}", timeout=15).content
                
                # Обработка через AI
                inv = process_invoice(image_bytes=img_bytes)
                self._send_invoice_report(token, chat_id, inv)
            except Exception as e:
                self._send_message(token, chat_id, f"❌ Ошибка обработки фото: {str(e)}")
            return

        # Обработка голосового сообщения (.ogg)
        if "voice" in message or "audio" in message:
            self._send_message(token, chat_id, "🎙️ *AI слушает голосовую приемку (казахский/русский язык)...*")
            voice_obj = message.get("voice") or message.get("audio")
            file_id = voice_obj["file_id"]
            
            try:
                f_resp = requests.get(f"https://api.telegram.org/bot{token}/getFile?file_id={file_id}", timeout=10)
                file_path = f_resp.json()["result"]["file_path"]
                audio_bytes = requests.get(f"https://api.telegram.org/file/bot{token}/{file_path}", timeout=15).content
                
                inv = process_invoice(audio_bytes=audio_bytes, audio_mime="audio/ogg")
                self._send_invoice_report(token, chat_id, inv)
            except Exception as e:
                self._send_message(token, chat_id, f"❌ Ошибка распознавания речи: {str(e)}")
            return

        # Обработка текстовых запросов
        text = message.get("text", "")
        if text:
            # Обработка текста приемки
            self._send_message(token, chat_id, "🔍 *AI парсит номенклатуру закупки...*")
            inv = process_invoice(voice_text=text)
            self._send_invoice_report(token, chat_id, inv)

    def _send_invoice_report(self, token: str, chat_id: int, inv: Dict[str, Any]):
        webapp_url = self.get_webapp_url()
        inv_num = inv.get("invoice_number", "б/н")
        cached_invoices[str(inv_num)] = inv

        supplier = str(inv.get("supplier_name") or "Не указан")
        total = to_float(inv.get("total_amount"), 0.0)
        items = inv.get("items") or []
        spikes = [it for it in items if it.get("is_price_increase")]

        lines = []
        if inv.get("transcription"):
            lines.append(f"🎙️ *Распознанная речь:* «{inv['transcription']}»\n")

        source_type = str(inv.get("source_type") or "")
        if "openai" in source_type:
            engine_badge = "🤖 *AI Engine: OpenAI (GPT-4o-mini + Whisper)*"
        elif "gemini" in source_type:
            engine_badge = "🤖 *AI Engine: Google Gemini 1.5 Flash*"
        else:
            engine_badge = "⚡ *AI Engine: Встроенный локальный движок*"
            
        lines.extend([
            f"📦 *Накладная: {inv_num}*",
            f"🏢 *Поставщик:* {supplier}",
            engine_badge,
            f"💰 *Общая сумма закупки:* {total:,.0f} ₸".replace(",", " "),
            f"📋 *Позиций принято:* {len(items)}",
            ""
        ])

        if items:
            lines.append("📝 *Принятые товары:*")
            for it in items[:8]:
                p_name = it.get("product_name") or it.get("raw_name") or "Товар"
                qty = to_float(it.get("quantity"), 1.0)
                unit = it.get("unit") or "шт"
                pr = to_float(it.get("purchase_price"), 0.0)
                tot = to_float(it.get("total_price"), qty * pr)
                lines.append(f" • {p_name}: *{qty:g} {unit}* × {pr:,.0f} ₸ = {tot:,.0f} ₸".replace(",", " "))
            if len(items) > 8:
                lines.append(f" _...и еще {len(items) - 8} поз._")
            lines.append("")

        if spikes:
            lines.append(f"🚨 *РАДАР МАРЖИ: ОБНАРУЖЕН РОСТ ЦЕН ({len(spikes)} поз.)!*")
            loss = to_float(inv.get("total_potential_loss_kzt"), 0.0)
            lines.append(f"⚠️ *Риск потери прибыли:* {loss:,.0f} ₸ на этой партии!\n".replace(",", " "))
            
            for s in spikes:
                p_name = s.get("product_name") or "Товар"
                old_p = to_float(s.get("previous_price"), 0.0)
                new_p = to_float(s.get("purchase_price"), 0.0)
                pct = to_float(s.get("price_change_pct"), 0.0)
                rec_ret = to_float(s.get("recommended_retail_price"), new_p * 1.25)
                lines.append(
                    f"🔻 *{p_name}*\n"
                    f"   Закуп: {old_p:,.0f} ₸ ➔ *{new_p:,.0f} ₸* (+{pct:.1f}%)\n"
                    f"   👉 Новая розница: *{rec_ret:,.0f} ₸*\n".replace(",", " ")
                )
        else:
            lines.append("✅ *Все закупочные цены стабильны и соответствуют контракту.*")

        msg_text = "\n".join(lines)
        kb = {
            "inline_keyboard": [
                [{"text": "💾 Занести в Google Sheets и 1C", "callback_data": f"sync_{inv_num}"}],
                [self._make_webapp_button("📱 Открыть Mini App в Telegram")]
            ]
        }
        self._send_message(token, chat_id, msg_text, reply_markup=kb)

bot_worker = TelegramBotWorker()
