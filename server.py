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
prod_count = cursor.fetchone()[0]
if prod_count == 0 and get_setting("catalog_cleared") != "true":
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
        
    env_webapp = os.getenv("WEBAPP_URL") or os.getenv("RENDER_EXTERNAL_URL")
    if not env_webapp:
        railway_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN") or os.getenv("RAILWAY_STATIC_URL")
        if railway_domain:
            if not railway_domain.startswith("http"):
                railway_domain = f"https://{railway_domain}"
            env_webapp = railway_domain

    if env_webapp:
        set_setting("webapp_url", env_webapp.rstrip("/"))
        
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

@app.get("/presentation", response_class=HTMLResponse)
@app.get("/pitch", response_class=HTMLResponse)
async def serve_presentation():
    pres_file = STATIC_DIR / "presentation.html"
    if pres_file.exists():
        return HTMLResponse(content=pres_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Презентация Sanau.AI загружается...</h1>")

@app.get("/presentation.pdf")
@app.get("/api/export/presentation")
async def serve_presentation_pdf():
    pdf_file = Path(__file__).resolve().parent / "presentation_pitch_deck.pdf"
    if not pdf_file.exists():
        try:
            from generate_pitch_deck_pdf import generate_pdf
            generate_pdf(str(pdf_file))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ошибка генерации PDF: {e}")
            
    return FileResponse(
        path=str(pdf_file),
        media_type="application/pdf",
        filename="Sanau_AI_Pitch_Deck.pdf"
    )

# ----------------- ПРОФИЛЬ МАГАЗИНА И НАСТРОЙКИ -----------------
class StoreProfilePayload(BaseModel):
    name: Optional[str] = "Магазин «Береке»"
    city: Optional[str] = "г. Тараз"
    owner: Optional[str] = "Владелец / Товаровед"
    target_margin_pct: Optional[float] = 25.0

class SettingsPayload(BaseModel):
    store_name: Optional[str] = None
    store_city: Optional[str] = None
    store_owner: Optional[str] = None
    store_margin: Optional[float] = None
    google_sheets_url: Optional[str] = None
    google_enabled: Optional[bool] = None
    telegram_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    telegram_enabled: Optional[bool] = None
    webhook_url: Optional[str] = None
    webhook_auth: Optional[str] = None
    webhook_enabled: Optional[bool] = None
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None

@app.get("/api/store")
async def get_store_profile():
    s = get_all_settings()
    return {
        "name": s.get("store_name", "Магазин «Береке»"),
        "city": s.get("store_city", "г. Тараз"),
        "owner": s.get("store_owner", "Владелец / Товаровед"),
        "target_margin_pct": float(s.get("store_margin", "25.0"))
    }

@app.post("/api/store")
async def update_store_profile(payload: StoreProfilePayload):
    if payload.name:
        set_setting("store_name", payload.name.strip())
    if payload.city:
        set_setting("store_city", payload.city.strip())
    if payload.owner:
        set_setting("store_owner", payload.owner.strip())
    if payload.target_margin_pct is not None:
        set_setting("store_margin", str(payload.target_margin_pct))
    return {
        "status": "success",
        "message": f"Профиль магазина «{payload.name or 'Мой магазин'}» успешно сохранен!"
    }

@app.get("/api/settings")
async def get_settings():
    s = get_all_settings()
    manager = IntegrationManager()
    all_connectors = manager.get_all_connectors()
    
    return {
        "store_name": s.get("store_name", "Магазин «Береке»"),
        "store_city": s.get("store_city", "г. Тараз"),
        "store_owner": s.get("store_owner", "Владелец / Товаровед"),
        "store_margin": float(s.get("store_margin", "25.0")),
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
    if payload.store_name is not None:
        set_setting("store_name", payload.store_name.strip())
    if payload.store_city is not None:
        set_setting("store_city", payload.store_city.strip())
    if payload.store_owner is not None:
        set_setting("store_owner", payload.store_owner.strip())
    if payload.store_margin is not None:
        set_setting("store_margin", str(payload.store_margin))
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
        
    return {"status": "success", "message": "Настройки магазина и сервисов успешно сохранены"}

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
    if analyzed.get("items") and not analyzed.get("error"):
        from services.connectors.sql_connector import SqlDatabaseConnector
        SqlDatabaseConnector().sync_invoice(analyzed)
    return analyzed

@app.post("/api/process/voice")
async def process_voice(file: UploadFile = File(...)):
    audio_bytes = await file.read()
    mime = file.content_type or "audio/ogg"
    analyzed = process_invoice(audio_bytes=audio_bytes, audio_mime=mime)
    if analyzed.get("items") and not analyzed.get("error"):
        from services.connectors.sql_connector import SqlDatabaseConnector
        SqlDatabaseConnector().sync_invoice(analyzed)
    return analyzed

class TextPayload(BaseModel):
    text: str

@app.post("/api/process/text")
async def process_text(payload: TextPayload):
    analyzed = process_invoice(voice_text=payload.text)
    if analyzed.get("items") and not analyzed.get("error"):
        from services.connectors.sql_connector import SqlDatabaseConnector
        SqlDatabaseConnector().sync_invoice(analyzed)
    return analyzed

class DemoPayload(BaseModel):
    sample_id: str = "spike_milk_flour"

@app.post("/api/reset_demo")
async def reset_demo_database():
    set_setting("catalog_cleared", "false")
    seed()
    return {"status": "success", "message": "База данных сброшена к эталонным ценам Тараза (12 товаров)"}

@app.post("/api/process/demo")
async def process_demo(payload: DemoPayload):
    analyzed = process_invoice(sample_id=payload.sample_id)
    if analyzed.get("items") and not analyzed.get("error"):
        from services.connectors.sql_connector import SqlDatabaseConnector
        SqlDatabaseConnector().sync_invoice(analyzed)
    return analyzed

@app.post("/api/clear_data")
async def clear_store_data():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM invoice_items")
    cursor.execute("DELETE FROM invoices")
    cursor.execute("DELETE FROM sync_logs")
    cursor.execute("DELETE FROM products")
    conn.commit()
    conn.close()
    set_setting("catalog_cleared", "true")
    return {"status": "success", "message": "Каталог товаров и журнал накладных полностью очищены. База пуста."}

@app.delete("/api/products/{product_id}")
async def delete_product(product_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"Товар #{product_id} удален из каталога"}

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

@app.get("/api/invoices/latest")
async def get_latest_invoice():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT raw_data FROM invoices ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if row and row[0]:
        try:
            return json.loads(row[0])
        except Exception:
            pass
    return None

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
    
    stability = 100 if spikes_count == 0 else max(20, 100 - (spikes_count * 15))
    
    return {
        "invoices_count": inv_count,
        "total_spend_kzt": round(total_sum, 0),
        "spikes_count": spikes_count,
        "saved_margin_kzt": round(saved_margin, 0),
        "recent_spikes": recent_spikes,
        "stability_index_pct": stability
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
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
