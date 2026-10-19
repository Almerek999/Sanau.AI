#!/usr/bin/env python3
"""
Генератор печатных накладных для демо-выступления перед жюри (Sanau.AI).
Формирует 3 официальные казахстанские накладные (Форма З-2) в формате A4:
1. Кейс №1: Скрытый скачок цен на Молоко и Муку (Красный алерт радара, потеря маржи 4 000 тг)
2. Кейс №2: Мультиязычная накладная Тараза (Казахский/Русский язык, оптовик Аулие-Ата)
3. Кейс №3: Штатная поставка (Зеленый коридор, 100% стабильность, сквозной учет)
"""

import sys
from pathlib import Path
from reportlab.lib.pagesizes import A4, portrait
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Регистрация кириллических шрифтов
FONT_UNICODE = "/Library/Fonts/Arial Unicode.ttf"
FONT_REG = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"

if Path(FONT_UNICODE).exists():
    pdfmetrics.registerFont(TTFont("MainFont", FONT_UNICODE))
else:
    pdfmetrics.registerFont(TTFont("MainFont", FONT_REG))

if Path(FONT_BOLD).exists():
    pdfmetrics.registerFont(TTFont("BoldFont", FONT_BOLD))
else:
    pdfmetrics.registerFont(TTFont("BoldFont", FONT_REG))

PAGE_WIDTH, PAGE_HEIGHT = portrait(A4) # 595.27 x 841.89 pt

def draw_header_box(c, helper_text, helper_bg=colors.HexColor("#fef3c7"), helper_border=colors.HexColor("#f59e0b")):
    # Верхняя подсказка спикеру (для ориентации во время питча)
    c.setFillColor(helper_bg)
    c.setStrokeColor(helper_border)
    c.roundRect(30, PAGE_HEIGHT - 48, PAGE_WIDTH - 60, 26, 4, fill=True, stroke=True)
    c.setFillColor(colors.HexColor("#92400e"))
    c.setFont("BoldFont", 8)
    c.drawString(40, PAGE_HEIGHT - 35, helper_text)

def draw_invoice_page(c, invoice_meta, supplier_meta, buyer_meta, items, speaker_tip, tip_color="#b45309", tip_bg="#fef3c7"):
    c.setFillColor(colors.white)
    c.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=True, stroke=False)
    
    # 1. Подсказка спикеру
    draw_header_box(c, speaker_tip, helper_bg=colors.HexColor(tip_bg), helper_border=colors.HexColor(tip_color))
    
    # 2. Форма З-2 стандартная шапка (Министерство финансов РК)
    c.setFillColor(colors.HexColor("#475569"))
    c.setFont("MainFont", 6.5)
    c.drawRightString(PAGE_WIDTH - 30, PAGE_HEIGHT - 60, "Приложение 26 к приказу Министра финансов РК от 20.12.2012 г. № 562")
    c.drawRightString(PAGE_WIDTH - 30, PAGE_HEIGHT - 68, "Форма З-2 (код по ОКУД: 0503102)")
    
    # 3. Реквизиты сторон
    top_y = PAGE_HEIGHT - 82
    c.setStrokeColor(colors.HexColor("#94a3b8"))
    c.setLineWidth(0.6)
    c.line(30, top_y, PAGE_WIDTH - 30, top_y)
    
    # Левая колонка: Отправитель (Поставщик)
    c.setFont("BoldFont", 8)
    c.setFillColor(colors.HexColor("#0f172a"))
    c.drawString(30, top_y - 12, "Организация-отправитель (Поставщик):")
    c.setFont("MainFont", 8)
    c.drawString(30, top_y - 23, supplier_meta["name"])
    c.drawString(30, top_y - 34, f"БИН/ИИН: {supplier_meta['bin']}  •  Тел: {supplier_meta['phone']}")
    c.drawString(30, top_y - 45, f"Адрес склада: {supplier_meta['address']}")
    
    # Правая колонка: Получатель (Магазин Береке)
    c.setFont("BoldFont", 8)
    c.drawString(310, top_y - 12, "Организация-получатель (Покупатель):")
    c.setFont("MainFont", 8)
    c.drawString(310, top_y - 23, buyer_meta["name"])
    c.drawString(310, top_y - 34, f"ИИН: {buyer_meta['bin']}  •  Торговая точка: {buyer_meta['store']}")
    c.drawString(310, top_y - 45, f"Пункт разгрузки: {buyer_meta['address']}")
    
    c.line(30, top_y - 54, PAGE_WIDTH - 30, top_y - 54)
    
    # 4. Название документа крупно
    c.setFont("BoldFont", 13)
    c.setFillColor(colors.HexColor("#0f172a"))
    c.drawCentredString(PAGE_WIDTH / 2, top_y - 75, f"НАКЛАДНАЯ НА ОТПУСК ЗАПАСОВ НА СТОРОНУ № {invoice_meta['number']}")
    c.setFont("MainFont", 9)
    c.drawCentredString(PAGE_WIDTH / 2, top_y - 88, f"от «{invoice_meta['date']}» года  •  Договор поставки: {invoice_meta.get('contract', 'Основной № 12/Т')}")
    
    # 5. Таблица позиций
    table_y = top_y - 105
    col_x = [30, 52, 280, 315, 360, 420, 475, PAGE_WIDTH - 30]
    # 0: №, 1: Название, 2: Ед, 3: Кол-во, 4: Цена закуп, 5: Сумма, 6: Примечание/Розничная
    
    # Шапка таблицы
    c.setFillColor(colors.HexColor("#f1f5f9"))
    c.rect(col_x[0], table_y - 22, col_x[-1] - col_x[0], 22, fill=True, stroke=True)
    
    c.setFillColor(colors.HexColor("#0f172a"))
    c.setFont("BoldFont", 7.5)
    c.drawString(col_x[0] + 4, table_y - 15, "№")
    c.drawString(col_x[1] + 6, table_y - 15, "Наименование товара, характеристика")
    c.drawString(col_x[2] + 4, table_y - 15, "Ед.")
    c.drawRightString(col_x[4] - 6, table_y - 15, "Отпущено")
    c.drawRightString(col_x[5] - 6, table_y - 15, "Цена, тг")
    c.drawRightString(col_x[6] - 6, table_y - 15, "Сумма, тг")
    c.drawString(col_x[6] + 6, table_y - 15, "Статус контроля")
    
    # Разделительные линии шапки
    for x in col_x:
        c.line(x, table_y, x, table_y - 22)
        
    cur_y = table_y - 22
    row_height = 24
    total_qty = 0
    total_sum = 0
    
    for idx, it in enumerate(items, 1):
        # Чередование фона для читаемости
        if idx % 2 == 0:
            c.setFillColor(colors.HexColor("#f8fafc"))
            c.rect(col_x[0], cur_y - row_height, col_x[-1] - col_x[0], row_height, fill=True, stroke=False)
            
        c.setStrokeColor(colors.HexColor("#cbd5e1"))
        c.setLineWidth(0.5)
        c.line(col_x[0], cur_y - row_height, col_x[-1], cur_y - row_height)
        
        # Линии колонок
        for x in col_x:
            c.line(x, cur_y, x, cur_y - row_height)
            
        # Данные строки
        qty = it["qty"]
        price = it["price"]
        row_sum = qty * price
        total_qty += qty
        total_sum += row_sum
        
        c.setFillColor(colors.HexColor("#0f172a"))
        c.setFont("MainFont", 8)
        c.drawString(col_x[0] + 5, cur_y - 16, str(idx))
        
        # Название (если подорожало — помечаем слегка заметно)
        c.setFont("BoldFont" if it.get("spike") else "MainFont", 8)
        c.drawString(col_x[1] + 6, cur_y - 16, it["name"])
        
        c.setFont("MainFont", 8)
        c.drawString(col_x[2] + 5, cur_y - 16, it["unit"])
        c.drawRightString(col_x[4] - 6, cur_y - 16, f"{qty:g}")
        c.drawRightString(col_x[5] - 6, cur_y - 16, f"{price:,.0f}".replace(",", " "))
        c.setFont("BoldFont", 8)
        c.drawRightString(col_x[6] - 6, cur_y - 16, f"{row_sum:,.0f}".replace(",", " "))
        
        # Статус
        if it.get("spike"):
            c.setFillColor(colors.HexColor("#dc2626")) # красный
            c.setFont("BoldFont", 7)
            c.drawString(col_x[6] + 6, cur_y - 16, f"РОСТ ЦЕНЫ (+{it['spike_pct']}%)")
        else:
            c.setFillColor(colors.HexColor("#16a34a")) # зеленый
            c.setFont("MainFont", 7)
            c.drawString(col_x[6] + 6, cur_y - 16, "По контракту")
            
        cur_y -= row_height
        
    # ИТОГО строка
    c.setFillColor(colors.HexColor("#f1f5f9"))
    c.rect(col_x[0], cur_y - 20, col_x[-1] - col_x[0], 20, fill=True, stroke=True)
    for x in [col_x[0], col_x[4], col_x[6], col_x[-1]]:
        c.line(x, cur_y, x, cur_y - 20)
        
    c.setFillColor(colors.HexColor("#0f172a"))
    c.setFont("BoldFont", 8.5)
    c.drawString(col_x[1] + 6, cur_y - 14, "ИТОГО ПО НАКЛАДНОЙ:")
    c.drawRightString(col_x[4] - 6, cur_y - 14, f"{total_qty:g}")
    c.drawRightString(col_x[6] - 6, cur_y - 14, f"{total_sum:,.0f} тг".replace(",", " "))
    
    cur_y -= 20
    
    # 6. Прописью
    cur_y -= 14
    c.setFont("MainFont", 8)
    c.drawString(30, cur_y, f"Всего наименований: {len(items)}, на общую сумму: {total_sum:,.0f} тенге (НДС 12% включен).".replace(",", " "))
    
    # 7. Подписи сторон и печати
    cur_y -= 35
    c.setLineWidth(0.6)
    c.setStrokeColor(colors.HexColor("#64748b"))
    
    # Левая сторона (Поставщик)
    c.setFont("BoldFont", 8)
    c.drawString(30, cur_y, "Отпуск груза разрешил:")
    c.line(135, cur_y, 260, cur_y)
    c.setFont("MainFont", 7)
    c.drawCentredString(197, cur_y - 9, "(подпись / Ф.И.О.)")
    
    c.setFont("BoldFont", 8)
    c.drawString(30, cur_y - 28, "Отпустил экспедитор:")
    c.line(135, cur_y - 28, 260, cur_y - 28)
    c.setFont("MainFont", 7)
    c.drawCentredString(197, cur_y - 37, "(подпись / Ф.И.О.)")
    
    # Печать поставщика
    c.setStrokeColor(colors.HexColor("#1e40af"))
    c.setLineWidth(1.2)
    c.circle(197, cur_y - 68, 26, stroke=True, fill=False)
    c.setFont("BoldFont", 6.5)
    c.setFillColor(colors.HexColor("#1e40af"))
    c.drawCentredString(197, cur_y - 65, "М. П.")
    c.drawCentredString(197, cur_y - 74, "ДЛЯ НАКЛАДНЫХ")
    
    # Правая сторона (Получатель)
    c.setFillColor(colors.HexColor("#0f172a"))
    c.setFont("BoldFont", 8)
    c.drawString(310, cur_y, "По доверенности №:")
    c.line(405, cur_y, PAGE_WIDTH - 30, cur_y)
    c.setFont("MainFont", 7)
    c.drawCentredString(470, cur_y - 9, "Разовое поручение")
    
    c.setFont("BoldFont", 8)
    c.drawString(310, cur_y - 28, "Запасы принял товаровед:")
    c.line(425, cur_y - 28, PAGE_WIDTH - 30, cur_y - 28)
    c.setFont("MainFont", 7)
    c.drawCentredString(480, cur_y - 37, "(Магазин «Береке»)")
    
    # Штамп магазина
    c.setStrokeColor(colors.HexColor("#0f766e"))
    c.setLineWidth(1.2)
    c.roundRect(390, cur_y - 90, 140, 42, 4, stroke=True, fill=False)
    c.setFont("BoldFont", 7)
    c.setFillColor(colors.HexColor("#0f766e"))
    c.drawCentredString(460, cur_y - 65, "ИП МАЗАГИН «БЕРЕКЕ»")
    c.setFont("MainFont", 6.5)
    c.drawCentredString(460, cur_y - 74, "ГРУЗ ПРИНЯТ БЕЗ ПРЕТЕНЗИЙ")
    c.drawCentredString(460, cur_y - 83, f"Дата: {invoice_meta['date']}")
    
    # 8. Рамочка штрихкода внизу
    c.setStrokeColor(colors.HexColor("#94a3b8"))
    c.setLineWidth(0.5)
    c.line(30, 48, PAGE_WIDTH - 30, 48)
    c.setFont("MainFont", 6.5)
    c.setFillColor(colors.HexColor("#64748b"))
    c.drawString(30, 36, "Документ сформирован для демонстрации работы системы Sanau.AI на защите хакатона.")
    c.drawRightString(PAGE_WIDTH - 30, 36, f"Штрихкод накладной: *{invoice_meta['number']}*")
    
    c.showPage()

def generate_all_invoices(pdf_path: str):
    c = canvas.Canvas(pdf_path, pagesize=portrait(A4))
    
    # Общие данные покупателя (магазин в Таразе)
    buyer = {
        "name": "ИП «Магазин Береке» (Тараз)",
        "bin": "880512301948",
        "store": "Магазин «Береке» (у дома)",
        "address": "г. Тараз, 1-й микрорайон, д. 14Б"
    }
    
    # =========================================================================
    # СТРАНИЦА 1: КЕЙС №1 (ГЛАВНЫЙ ШОК-КЕЙС: РОСТ ЦЕН НА МОЛОКО И МУКУ)
    # =========================================================================
    inv1_meta = {
        "number": "Т-4819",
        "date": "20 октября 2026",
        "contract": "Договор дистрибьюции № 14-П от 12.01.2026"
    }
    supplier1 = {
        "name": "ТОО «Прима Дистрибьюшн Тараз»",
        "bin": "120440019283",
        "phone": "+7 (7262) 43-21-90",
        "address": "г. Тараз, Промзона, ул. Желтоксан 140"
    }
    items1 = [
        {"name": "Молоко 'Родина' 3.2% 1л", "unit": "шт", "qty": 30.0, "price": 450.0, "spike": True, "spike_pct": 15.4},
        {"name": "Мука пшеничная 'Цесна' 1-сорт 2кг", "unit": "шт", "qty": 20.0, "price": 790.0, "spike": True, "spike_pct": 16.2},
        {"name": "Чай черный 'Пиала Gold' 250г", "unit": "шт", "qty": 15.0, "price": 950.0, "spike": False},
        {"name": "Макароны 'Султан' Спагетти 400г", "unit": "шт", "qty": 25.0, "price": 320.0, "spike": False},
        {"name": "Вода 'Tassay' негазированная 1.5л", "unit": "шт", "qty": 24.0, "price": 170.0, "spike": False}
    ]
    tip1 = "[КЕЙС 1: РОСТ ЦЕН] Молоко (450 тг вместо 390) + Мука (790 тг вместо 680). Радар выявит потерю маржи 4 000 тг!"
    draw_invoice_page(c, inv1_meta, supplier1, buyer, items1, tip1, tip_color="#dc2626", tip_bg="#fee2e2")
    
    # =========================================================================
    # СТРАНИЦА 2: КЕЙС №2 (КАЗАХСКИЙ ЯЗЫК, ОПТОВИК САХПОСЕЛОК / АУЛИЕ-АТА)
    # =========================================================================
    inv2_meta = {
        "number": "АТА-104",
        "date": "20 октября 2026",
        "contract": "Көтерме сату шарты № 88/А"
    }
    supplier2 = {
        "name": "ЖК «Ахметов Қ.С.» (Оптовый склад Аулие-Ата)",
        "bin": "790815302194",
        "phone": "+7 (707) 999-88-77",
        "address": "Тараз қ., Сахпоселок, «Аулие-Ата» көтерме базары, 4-қойма"
    }
    items2 = [
        {"name": "Күнбағыс майы 'Шедевр' 1л", "unit": "құты", "qty": 25.0, "price": 840.0, "spike": True, "spike_pct": 12.0},
        {"name": "Қант құмы (Сахар песок) 1кг", "unit": "кг", "qty": 50.0, "price": 410.0, "spike": False},
        {"name": "Күріш 'Ақмаржан' (Рис) 1кг", "unit": "кг", "qty": 20.0, "price": 520.0, "spike": False},
        {"name": "Конфет 'Баян Сұлу' Қазақстандық", "unit": "кг", "qty": 10.0, "price": 2100.0, "spike": False},
        {"name": "Шоколад 'Қазақстан' Рахат 100г", "unit": "дана", "qty": 30.0, "price": 650.0, "spike": False}
    ]
    tip2 = "[КЕЙС 2: ҚАЗАҚША] Оптовик Аулие-Ата. Подорожание масла Шедевр (840 тг вместо 750). Проверка мультиязычности!"
    draw_invoice_page(c, inv2_meta, supplier2, buyer, items2, tip2, tip_color="#0284c7", tip_bg="#e0f2fe")
    
    # =========================================================================
    # СТРАНИЦА 3: КЕЙС №3 (ШТАТНАЯ НАКЛАДНАЯ: ЗЕЛЕНЫЙ КОРИДОР)
    # =========================================================================
    inv3_meta = {
        "number": "РГ-3022",
        "date": "20 октября 2026",
        "contract": "Генеральный контракт RG-Taraz № 05-24"
    }
    supplier3 = {
        "name": "ТОО «RG Brands Тараз»",
        "bin": "050240003192",
        "phone": "+7 (7262) 55-40-10",
        "address": "г. Тараз, Сулейменова 22, логистический хаб"
    }
    items3 = [
        {"name": "Вода 'Tassay' негазированная 1.5л", "unit": "шт", "qty": 60.0, "price": 170.0, "spike": False},
        {"name": "Чай черный 'Пиала Gold' 250г", "unit": "шт", "qty": 20.0, "price": 950.0, "spike": False},
        {"name": "Макароны 'Султан' Спагетти 400г", "unit": "шт", "qty": 30.0, "price": 320.0, "spike": False},
        {"name": "Рис 'Акмаржан' 1кг", "unit": "кг", "qty": 25.0, "price": 520.0, "spike": False}
    ]
    tip3 = "[КЕЙС 3: ЗЕЛЕНЫЙ КОРИДОР] Штатная накладная: 100% стабильность цен, моментальный учет в 1С и Google Sheets"
    draw_invoice_page(c, inv3_meta, supplier3, buyer, items3, tip3, tip_color="#16a34a", tip_bg="#dcfce7")
    
    c.save()
    print(f"✅ Файл печатных накладных успешно создан: {pdf_path}")

if __name__ == "__main__":
    out = "demo_assets/invoices_for_jury_demo.pdf"
    if len(sys.argv) > 1:
        out = sys.argv[1]
    generate_all_invoices(out)
