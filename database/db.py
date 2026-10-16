import sqlite3
import json
from pathlib import Path
from config import DB_PATH

def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.create_function("lower", 1, lambda s: s.lower() if s else "")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Таблица товаров
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        category TEXT,
        unit TEXT DEFAULT 'шт',
        current_purchase_price REAL NOT NULL,
        recommended_retail_price REAL NOT NULL,
        target_margin_pct REAL DEFAULT 20.0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Таблица поставщиков
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        contact TEXT,
        city TEXT DEFAULT 'Тараз',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Таблица накладных
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_number TEXT,
        supplier_name TEXT NOT NULL,
        date TEXT,
        total_amount REAL,
        status TEXT DEFAULT 'processed',
        source_type TEXT DEFAULT 'photo', -- 'photo', 'voice', 'manual'
        raw_data JSON,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Таблица позиций накладной
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS invoice_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id INTEGER,
        product_name TEXT NOT NULL,
        quantity REAL NOT NULL,
        unit TEXT DEFAULT 'шт',
        purchase_price REAL NOT NULL,
        previous_price REAL,
        price_change_pct REAL DEFAULT 0.0,
        is_price_increase BOOLEAN DEFAULT 0,
        total_price REAL NOT NULL,
        FOREIGN KEY (invoice_id) REFERENCES invoices(id)
    )
    """)
    
    # Журнал синхронизации с внешними сервисами
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sync_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        service_name TEXT NOT NULL,
        target_destination TEXT,
        status TEXT NOT NULL, -- 'SUCCESS', 'FAILED'
        items_count INTEGER DEFAULT 0,
        response_message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Таблица пользовательских настроек и привязок сервисов
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    conn.commit()
    conn.close()

def get_setting(key: str, default: str = "") -> str:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row and row[0] is not None else default
    except Exception:
        return default

def set_setting(key: str, value: str):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO settings (key, value, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value,
            updated_at = CURRENT_TIMESTAMP
        """, (key, str(value)))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error saving setting {key}: {e}")

def get_all_settings() -> dict:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM settings")
        rows = cursor.fetchall()
        conn.close()
        return {r["key"]: r["value"] for r in rows}
    except Exception:
        return {}

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at", DB_PATH)
