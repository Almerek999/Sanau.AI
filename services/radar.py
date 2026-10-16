from typing import Dict, Any, List
from database.db import get_connection

def find_existing_product(name: str):
    """Поиск товара в каталоге с нечетким сопоставлением"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Точное совпадение
    cursor.execute("SELECT * FROM products WHERE LOWER(name) = LOWER(?)", (name.strip(),))
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

def analyze_invoice_pricing(raw_invoice: Dict[str, Any]) -> Dict[str, Any]:
    """
    Анализ маржинальности и детекция подорожаний
    """
    items = raw_invoice.get("items", [])
    analyzed_items = []
    
    total_potential_loss = 0.0
    spikes_count = 0
    total_sum = 0.0
    
    for it in items:
        p_name = it.get("product_name", "").strip()
        new_price = float(it.get("purchase_price", 0.0))
        qty = float(it.get("quantity", 1.0))
        total_line = new_price * qty
        total_sum += total_line
        
        existing = find_existing_product(p_name)
        
        if existing:
            old_price = float(existing.get("current_purchase_price", new_price))
            curr_retail = float(existing.get("recommended_retail_price", old_price * 1.25))
            target_margin_pct = float(existing.get("target_margin_pct", 20.0))
            
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
                "product_name": existing["name"],
                "raw_name": p_name,
                "category": existing.get("category", "Общее"),
                "quantity": qty,
                "unit": it.get("unit", existing.get("unit", "шт")),
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
                "category": it.get("category", "Новый товар"),
                "quantity": qty,
                "unit": it.get("unit", "шт"),
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
    
    return {
        "invoice_number": raw_invoice.get("invoice_number", "б/н"),
        "supplier_name": raw_invoice.get("supplier_name", "ТОО 'Дистрибьютор'"),
        "date": raw_invoice.get("date", "Сегодня"),
        "total_amount": round(total_sum, 0),
        "items": analyzed_items,
        "items_count": len(analyzed_items),
        "spikes_count": spikes_count,
        "total_potential_loss_kzt": round(total_potential_loss, 0),
        "supplier_stability_score": stability_score,
        "source_type": raw_invoice.get("source_type", "photo")
    }
