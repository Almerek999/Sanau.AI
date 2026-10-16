import os
import io
import time
import json
import sqlite3
import openpyxl
from typing import Optional, Dict, Any
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database.db import init_db, get_connection, get_all_settings, set_setting, get_setting
from database.seed_data import seed
from services.ai_engine import process_invoice, get_demo_sample_invoice
from services.radar import analyze_invoice_pricing
from services.connectors.manager import IntegrationManager
from bot import bot_worker
import config

# Создаем папку static если её нет
STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(exist_ok=True)

# Инициализируем БД
init_db()
conn = get_connection()
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM products")
if cursor.fetchone()[0] == 0:
    seed()
conn.close()

app = FastAPI(title="Sanau.AI API", version="2.0")

@app.on_event("startup")
def on_startup():
    # Автоматическая синхронизация ключей из .env в БД (не нужно вводить вручную в сервисы)
    if config.OPENAI_API_KEY and not get_setting("openai_api_key"):
        set_setting("openai_api_key", config.OPENAI_API_KEY)
    if config.GEMINI_API_KEY and not get_setting("gemini_api_key"):
        set_setting("gemini_api_key", config.GEMINI_API_KEY)
    if config.TELEGRAM_BOT_TOKEN and not get_setting("telegram_token"):
        set_setting("telegram_token", config.TELEGRAM_BOT_TOKEN)
    bot_worker.start()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- СТАТИКА И МИНИ-ПРИЛОЖЕНИЕ -----------------
@app.get("/", response_class=HTMLResponse)
@app.get("/miniapp", response_class=HTMLResponse)
async def serve_miniapp():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Sanau.AI Mini App загружается...</h1>")

# ----------------- НАСТРОЙКИ И ПРИВЯЗКА СЕРВИСОВ -----------------
class SettingsPayload(BaseModel):
    google_sheets_url: Optional[str] = ""
    google_enabled: Optional[bool] = True
    telegram_token: Optional[str] = ""
    telegram_chat_id: Optional[str] = ""
    telegram_enabled: Optional[bool] = True
    webhook_url: Optional[str] = ""
    webhook_auth: Optional[str] = ""
    webhook_enabled: Optional[bool] = True
    gemini_api_key: Optional[str] = ""
    openai_api_key: Optional[str] = ""

@app.get("/api/settings")
async def get_settings():
    s = get_all_settings()
    manager = IntegrationManager()
    all_connectors = manager.get_all_connectors()
    
    return {
        "google_sheets_url": s.get("google_sheets_url", ""),
        "google_enabled": s.get("google_enabled", "true") == "true",
        "telegram_token": s.get("telegram_token", config.TELEGRAM_BOT_TOKEN),
        "telegram_chat_id": s.get("telegram_chat_id", config.TELEGRAM_DEFAULT_CHAT_ID),
        "telegram_enabled": s.get("telegram_enabled", "true") == "true",
        "webhook_url": s.get("webhook_url", config.DEFAULT_WEBHOOK_URL or "https://webhook.site/demo-sanau"),
        "webhook_auth": s.get("webhook_auth", ""),
        "webhook_enabled": s.get("webhook_enabled", "true") == "true",
        "gemini_api_key_configured": bool(s.get("gemini_api_key") or config.GEMINI_API_KEY),
        "openai_api_key_configured": bool(s.get("openai_api_key") or config.OPENAI_API_KEY),
        "active_services": {
            c.name: {
                "enabled": c.enabled,
                "target": getattr(c, "webhook_url", "") or getattr(c, "endpoint_url", "") or getattr(c, "chat_id", "") or "Локальный"
            }
            for c in all_connectors
        }
    }

@app.post("/api/settings")
async def update_settings(payload: SettingsPayload):
    if payload.google_sheets_url is not None:
        set_setting("google_sheets_url", payload.google_sheets_url)
    if payload.google_enabled is not None:
        set_setting("google_enabled", "true" if payload.google_enabled else "false")
    if payload.telegram_token is not None:
        token_clean = payload.telegram_token.strip()
        set_setting("telegram_token", token_clean)
        if token_clean:
            bot_worker.start(force_restart=True)
    if payload.telegram_chat_id is not None:
        set_setting("telegram_chat_id", payload.telegram_chat_id.strip())
    if payload.telegram_enabled is not None:
        set_setting("telegram_enabled", "true" if payload.telegram_enabled else "false")
    if payload.webhook_url is not None:
        set_setting("webhook_url", payload.webhook_url)
    if payload.webhook_auth is not None:
        set_setting("webhook_auth", payload.webhook_auth)
    if payload.webhook_enabled is not None:
        set_setting("webhook_enabled", "true" if payload.webhook_enabled else "false")
    if payload.gemini_api_key is not None and payload.gemini_api_key.strip():
        set_setting("gemini_api_key", payload.gemini_api_key.strip())
    if payload.openai_api_key is not None and payload.openai_api_key.strip():
        set_setting("openai_api_key", payload.openai_api_key.strip())
        
    return {"status": "success", "message": "Настройки сервисов и API ключи успешно сохранены и привязаны"}

@app.post("/api/test_connector")
async def test_connector(req: Dict[str, str]):
    connector_type = req.get("type", "all")
    manager = IntegrationManager()
    
    if connector_type == "google":
        res = manager.google_conn.test_connection()
        return res.model_dump()
    elif connector_type == "telegram":
        res = manager.tg_conn.test_connection()
        return res.model_dump()
    elif connector_type == "webhook":
        res = manager.webhook_conn.test_connection()
        return res.model_dump()
    elif connector_type == "sql":
        res = manager.sql_conn.test_connection()
        return res.model_dump()
    else:
        results = manager.test_all()
        return [r.model_dump() for r in results]

# ----------------- ПРИЕМ И ОБРАБОТКА НАКЛАДНЫХ -----------------
@app.post("/api/process/photo")
async def process_photo(file: UploadFile = File(...)):
    image_bytes = await file.read()
    analyzed = process_invoice(image_bytes=image_bytes)
    return analyzed

@app.post("/api/process/voice")
async def process_voice(file: UploadFile = File(...)):
    audio_bytes = await file.read()
    mime = file.content_type or "audio/ogg"
    analyzed = process_invoice(audio_bytes=audio_bytes, audio_mime=mime)
    return analyzed

class TextPayload(BaseModel):
    text: str

@app.post("/api/process/text")
async def process_text(payload: TextPayload):
    analyzed = process_invoice(voice_text=payload.text)
    return analyzed

class DemoPayload(BaseModel):
    sample_id: str = "spike_milk_flour"

@app.post("/api/reset_demo")
async def reset_demo_database():
    seed()
    return {"status": "success", "message": "База данных сброшена к эталонным ценам Тараза (молоко 390 ₸, мука 680 ₸)"}

@app.post("/api/process/demo")
async def process_demo(payload: DemoPayload):
    analyzed = process_invoice(sample_id=payload.sample_id)
    return analyzed

# ----------------- СИНХРОНИЗАЦИЯ ВО ВСЕ СЕРВИСЫ -----------------
@app.post("/api/sync")
async def sync_invoice_to_services(invoice_data: Dict[str, Any]):
    manager = IntegrationManager()
    results = manager.sync_to_all(invoice_data)
    return {
        "status": "success",
        "results": [r.model_dump() for r in results]
    }

# ----------------- ДАННЫЕ ДЛЯ МИНИ-ПРИЛОЖЕНИЯ -----------------
@app.get("/api/products")
async def get_products():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, name, category, unit, current_purchase_price, recommended_retail_price, target_margin_pct, updated_at
    FROM products ORDER BY id ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/api/invoices")
async def get_invoices():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, invoice_number, supplier_name, date, total_amount, status, source_type, created_at
    FROM invoices ORDER BY id DESC LIMIT 50
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/api/radar")
async def get_radar_stats():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Считаем общее число накладных и сумму закупа
    cursor.execute("SELECT COUNT(*), COALESCE(SUM(total_amount), 0) FROM invoices")
    inv_count, total_sum = cursor.fetchone()
    
    # Позиции с ростом цен
    cursor.execute("""
    SELECT COUNT(*), COALESCE(SUM((purchase_price - previous_price) * quantity), 0)
    FROM invoice_items
    WHERE is_price_increase = 1
    """)
    spikes_count, saved_margin = cursor.fetchone()
    
    # Топ недавних подорожаний
    cursor.execute("""
    SELECT ii.product_name, i.supplier_name, ii.previous_price, ii.purchase_price,
           ii.price_change_pct, ii.quantity, ii.unit, i.created_at
    FROM invoice_items ii
    JOIN invoices i ON ii.invoice_id = i.id
    WHERE ii.is_price_increase = 1
    ORDER BY ii.id DESC LIMIT 10
    """)
    recent_spikes = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    # Дополняем эталонными данными, если накладных мало
    if not recent_spikes:
        recent_spikes = [
            {"product_name": "Молоко 'Родина' 3.2% 1л", "supplier_name": "ТОО 'Прима Дистрибьюшн'", "previous_price": 390, "purchase_price": 440, "price_change_pct": 12.8, "quantity": 25, "unit": "шт"},
            {"product_name": "Мука пшеничная 'Цесна' 2кг", "supplier_name": "ТОО 'Прима Дистрибьюшн'", "previous_price": 680, "purchase_price": 760, "price_change_pct": 11.7, "quantity": 10, "unit": "шт"},
            {"product_name": "Масло растительное 'Шедевр' 1л", "supplier_name": "ИП 'Ахметов' (Аулие-Ата)", "previous_price": 750, "purchase_price": 840, "price_change_pct": 12.0, "quantity": 20, "unit": "шт"},
            {"product_name": "Сыр 'President' Сливочный 200г", "supplier_name": "ТОО 'Эмиль'", "previous_price": 1100, "purchase_price": 1250, "price_change_pct": 13.6, "quantity": 10, "unit": "шт"},
        ]
        spikes_count = max(spikes_count, len(recent_spikes))
        saved_margin = max(saved_margin, 38400.0)
        
    return {
        "invoices_count": max(inv_count, 18),
        "total_spend_kzt": max(total_sum, 642800.0),
        "spikes_count": spikes_count,
        "saved_margin_kzt": saved_margin,
        "recent_spikes": recent_spikes,
        "stability_index_pct": 87
    }

@app.get("/api/sync_logs")
async def get_sync_logs():
    return IntegrationManager.get_recent_logs(limit=25)

# ----------------- ЭКСПОРТ ДАННЫХ -----------------
@app.get("/api/export/{fmt}")
async def export_data(fmt: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, category, unit, current_purchase_price, recommended_retail_price, target_margin_pct FROM products")
    products = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT id, invoice_number, supplier_name, date, total_amount, status FROM invoices")
    invoices = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    if fmt == "excel":
        wb = openpyxl.Workbook()
        ws_prod = wb.active
        ws_prod.title = "Номенклатура"
        ws_prod.append(["ID", "Название", "Категория", "Ед. изм.", "Закупочная цена (₸)", "Реком. розница (₸)", "Маржа (%)"])
        for p in products:
            ws_prod.append([p.get("id"), p.get("name"), p.get("category"), p.get("unit"), p.get("current_purchase_price"), p.get("recommended_retail_price"), p.get("target_margin_pct")])
            
        ws_inv = wb.create_sheet(title="Накладные")
        ws_inv.append(["ID", "Номер накладной", "Поставщик", "Дата", "Сумма (₸)", "Статус"])
        for inv in invoices:
            ws_inv.append([inv.get("id"), inv.get("invoice_number"), inv.get("supplier_name"), inv.get("date"), inv.get("total_amount"), inv.get("status")])
            
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return Response(
            content=buf.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=sanau_taraz.xlsx"}
        )
    elif fmt == "xml":
        xml_str = f"""<?xml version="1.0" encoding="UTF-8"?>
<КоммерческаяИнформация ВерсияСхемы="2.09" ДатаФормирования="{time.strftime('%Y-%m-%d')}">
  <Каталог СодержитТовары="true">
    <Ид>SANAU-TARAZ-001</Ид>
    <Наименование>Основной каталог Sanau.AI Тараз</Наименование>
    <Товары>
"""
        for p in products:
            xml_str += f"""      <Товар>
        <Ид>{p.get('id')}</Ид>
        <Наименование>{p.get('name')}</Наименование>
        <БазоваяЕдиница>{p.get('unit')}</БазоваяЕдиница>
        <ЦенаЗакупки>{p.get('current_purchase_price')}</ЦенаЗакупки>
        <ЦенаПродажи>{p.get('recommended_retail_price')}</ЦенаПродажи>
      </Товар>\n"""
        xml_str += """    </Товары>
  </Каталог>
</КоммерческаяИнформация>"""
        return Response(
            content=xml_str,
            media_type="application/xml",
            headers={"Content-Disposition": "attachment; filename=sanau_1c.xml"}
        )
    elif fmt == "kaspi":
        lines = ["model;price;availabilities"]
        for p in products:
            lines.append(f"{p.get('name')};{p.get('recommended_retail_price')};yes")
        csv_bytes = "\n".join(lines).encode("utf-8")
        return Response(
            content=csv_bytes,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=kaspi_feed.csv"}
        )
    else:
        raise HTTPException(status_code=400, detail="Unknown format")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
