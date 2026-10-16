import sqlite3
import os
import json
from database.db import init_db, get_connection
from database.seed_data import seed
from services.radar import find_existing_product, analyze_invoice_pricing
from services.ai_engine import get_demo_sample_invoice, process_invoice
from services.connectors.manager import IntegrationManager
from services.connectors.sql_connector import SqlDatabaseConnector
from services.connectors.google_sheets import GoogleSheetsConnector
from services.connectors.telegram_notifier import TelegramConnector
from services.connectors.webhook_connector import WebhookConnector

def test_database_init_and_seed():
    init_db()
    seed()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM products")
    p_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM suppliers")
    s_count = cursor.fetchone()[0]
    conn.close()
    
    assert p_count >= 10, f"Ожидалось не менее 10 товаров, получено {p_count}"
    assert s_count >= 3, f"Ожидалось не менее 3 поставщиков, получено {s_count}"

def test_radar_price_spike_detection():
    # Тест накладной с подорожанием молока
    sample = get_demo_sample_invoice("spike_milk_flour")
    analyzed = analyze_invoice_pricing(sample)
    
    assert analyzed["spikes_count"] >= 1, "Радар должен был зафиксировать рост цен"
    assert analyzed["total_potential_loss_kzt"] > 0, "Должен быть рассчитан риск потери маржи"
    
    # Проверяем конкретную позицию - Молоко Родина
    milk_item = next(it for it in analyzed["items"] if "Родина" in it["product_name"])
    assert milk_item["is_price_increase"] is True
    assert milk_item["purchase_price"] == 440.0
    assert milk_item["previous_price"] == 390.0
    assert milk_item["recommended_retail_price"] > milk_item["purchase_price"]

def test_sql_connector_sync():
    conn_sql = SqlDatabaseConnector()
    sample = get_demo_sample_invoice("spike_milk_flour")
    analyzed = analyze_invoice_pricing(sample)
    
    res = conn_sql.sync_invoice(analyzed)
    assert res.success is True
    assert res.records_synced == len(analyzed["items"])
    
    # Проверяем, что в БД действительно появилась накладная
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM invoices WHERE invoice_number = ?", (analyzed["invoice_number"],))
    count = cursor.fetchone()[0]
    conn.close()
    assert count >= 1

def test_connectors_formatting():
    sample = get_demo_sample_invoice("spike_milk_flour")
    analyzed = analyze_invoice_pricing(sample)
    
    # Google Sheets connector
    gs = GoogleSheetsConnector(webhook_url="")
    res_gs = gs.sync_invoice(analyzed)
    assert res_gs.success is True
    assert res_gs.records_synced == len(analyzed["items"])
    
    # Telegram connector fallback
    tg = TelegramConnector(bot_token="", chat_id="")
    res_tg = tg.sync_invoice(analyzed)
    assert res_tg.success is True
    
    # Webhook connector
    wh = WebhookConnector(endpoint_url="")
    res_wh = wh.sync_invoice(analyzed)
    assert res_wh.success is True

def test_integration_manager():
    manager = IntegrationManager({
        "sql_enabled": True,
        "google_enabled": True,
        "google_sheets_url": "",
        "telegram_enabled": True,
        "telegram_token": "",
        "webhook_enabled": True,
        "webhook_url": ""
    })
    sample = get_demo_sample_invoice("spike_milk_flour")
    analyzed = analyze_invoice_pricing(sample)
    
    results = manager.sync_to_all(analyzed)
    assert len(results) == 4
    assert all(r.success for r in results)

if __name__ == "__main__":
    test_database_init_and_seed()
    test_radar_price_spike_detection()
    test_sql_connector_sync()
    test_connectors_formatting()
    test_integration_manager()
    print("ALL TESTS PASSED SUCCESSFULLY! 🚀")
