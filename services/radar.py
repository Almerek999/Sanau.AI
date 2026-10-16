from typing import Dict, Any, List
from database.db import get_connection

def find_existing_product(name: str):
    """Поиск товара в каталоге с нечетким сопоставлением"""
    if not name or not isinstance(name, str):
        return None
    name_str = name.strip()
    if not name_str:
        return None
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Точное совпадение
    cursor.execute("SELECT * FROM products WHERE LOWER(name) = LOWER(?)", (name_str,))
    row = cursor.fetchone()
    if row:
        conn.close()
        return dict(row)
        
    # 2. Поиск по ключевым словам (например 'Родина', 'Цесна', 'Шедевр')
    tokens = [t.lower() for t in name.replace("'", "").replace('"', '').split() if len(t) > 3]
    for token in tokens:
        cursor.execute("SELECT * FROM products WHERE LOWER(name) LIKE ?", (f"%{token}%",))
        candidate = cursor.fetchone()
        if candidate:
            conn.close()
            return dict(candidate)
            
    conn.close()
    return None

def to_float(val: Any, default: float = 0.0) -> float:
    """Безопасная конвертация любых значений (включая None, строки с пробелами и валютами) в float"""
    if val is None:
        return default
    try:
        if isinstance(val, (int, float)):
            return float(val)
        cleaned = str(val).replace("₸", "").replace("тг", "").replace(" ", "").replace(",", ".").strip()
        if not cleaned or cleaned.lower() == "none" or cleaned.lower() == "null":
            return default
        return float(cleaned)
    except Exception:
        return default

def analyze_invoice_pricing(raw_invoice: Dict[str, Any]) -> Dict[str, Any]:
    """
    Анализ маржинальности и детекция подорожаний
    """
    if not isinstance(raw_invoice, dict):
        raw_invoice = {}

    items = raw_invoice.get("items") or []
    analyzed_items = []
    
    total_potential_loss = 0.0
    spikes_count = 0
    total_sum = 0.0
    
    for it in items:
        if not isinstance(it, dict):
            continue
            
        p_name = str(it.get("product_name") or it.get("raw_name") or "Товар").strip()
        new_price = to_float(it.get("purchase_price"), 0.0)
        qty = to_float(it.get("quantity"), 1.0)
        if qty <= 0:
            qty = 1.0
            
        total_line = to_float(it.get("total_price"), new_price * qty)
        if total_line <= 0 and new_price > 0:
            total_line = new_price * qty
            
        total_sum += total_line
        
        existing = find_existing_product(p_name)
        
        if existing:
            old_price = to_float(existing.get("current_purchase_price"), new_price)
            if old_price <= 0:
                old_price = new_price
            curr_retail = to_float(existing.get("recommended_retail_price"), old_price * 1.25)
            target_margin_pct = to_float(existing.get("target_margin_pct"), 20.0)
            
            diff = new_price - old_price
            diff_pct = (diff / old_price * 100.0) if old_price > 0 else 0.0
            
            # Подорожание больше 2.5%
            is_spike = diff_pct > 2.5
            if is_spike:
                spikes_count += 1
                # Потеря маржи = разница в закупке * объем партии
                loss_on_batch = diff * qty
                total_potential_loss += loss_on_batch
                
                # Расчет новой розничной цены для удержания маржи
                rec_retail = round(new_price / (1.0 - target_margin_pct / 100.0), -1)
                if rec_retail < new_price * 1.05:
                    rec_retail = round(new_price * 1.25, -1)
            else:
                rec_retail = curr_retail
                
            analyzed_items.append({
                "product_name": existing.get("name") or p_name,
                "raw_name": p_name,
                "category": existing.get("category", "Общее"),
                "quantity": qty,
                "unit": str(it.get("unit") or existing.get("unit") or "шт"),
                "purchase_price": new_price,
                "previous_price": old_price,
                "price_change_pct": round(diff_pct, 1),
                "is_price_increase": is_spike,
                "recommended_retail_price": rec_retail,
                "current_retail_price": curr_retail,
                "total_price": total_line,
                "margin_loss_batch_kzt": round(diff * qty, 0) if is_spike else 0.0
            })
        else:
            # Новый товар
            default_retail = round(new_price * 1.25, -1)
            analyzed_items.append({
                "product_name": p_name,
                "raw_name": p_name,
                "category": str(it.get("category") or "Новый товар"),
                "quantity": qty,
                "unit": str(it.get("unit") or "шт"),
                "purchase_price": new_price,
                "previous_price": None,
                "price_change_pct": 0.0,
                "is_price_increase": False,
                "recommended_retail_price": default_retail,
                "current_retail_price": default_retail,
                "total_price": total_line,
                "margin_loss_batch_kzt": 0.0
            })
            
    # Индекс стабильности поставщика: если 0 подорожаний = 100%, иначе снижается
    stability_score = max(0, 100 - (spikes_count * 25))
    final_total = round(total_sum, 0) if total_sum > 0 else round(to_float(raw_invoice.get("total_amount")), 0)
    
    return {
        "invoice_number": str(raw_invoice.get("invoice_number") or "б/н"),
        "supplier_name": str(raw_invoice.get("supplier_name") or "ТОО 'Дистрибьютор'"),
        "date": str(raw_invoice.get("date") or "Сегодня"),
        "total_amount": final_total,
        "items": analyzed_items,
        "items_count": len(analyzed_items),
        "spikes_count": spikes_count,
        "total_potential_loss_kzt": round(total_potential_loss, 0),
        "supplier_stability_score": stability_score,
        "source_type": str(raw_invoice.get("source_type") or "photo"),
        "transcription": str(raw_invoice.get("transcription") or ""),
        "note": str(raw_invoice.get("note") or "")
    }
