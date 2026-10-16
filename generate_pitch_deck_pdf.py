import os
import sys
from pathlib import Path
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Регистрация кириллических и Unicode шрифтов
FONT_UNICODE_PATH = "/Library/Fonts/Arial Unicode.ttf"
FONT_BOLD_PATH = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_REG_PATH = "/System/Library/Fonts/Supplemental/Arial.ttf"

if Path(FONT_UNICODE_PATH).exists():
    pdfmetrics.registerFont(TTFont("MainFont", FONT_UNICODE_PATH))
else:
    pdfmetrics.registerFont(TTFont("MainFont", FONT_REG_PATH))

if Path(FONT_BOLD_PATH).exists():
    pdfmetrics.registerFont(TTFont("BoldFont", FONT_BOLD_PATH))
else:
    pdfmetrics.registerFont(TTFont("BoldFont", FONT_REG_PATH))

# Цветовая палитра
BG_DARK = colors.HexColor("#070a13")      # deep dark
CARD_DARK = colors.HexColor("#0f172a")    # slate-900
PRIMARY = colors.HexColor("#4f46e5")      # indigo-600
PRIMARY_LIGHT = colors.HexColor("#6366f1")# indigo-500
ACCENT_SKY = colors.HexColor("#0284c7")   # sky-600
ACCENT_CYAN = colors.HexColor("#38bdf8")  # sky-400
ACCENT_GREEN = colors.HexColor("#10b981") # emerald-500
ACCENT_ROSE = colors.HexColor("#f43f5e")  # rose-500
ACCENT_AMBER = colors.HexColor("#f59e0b") # amber-500
TEXT_WHITE = colors.HexColor("#ffffff")
TEXT_MUTED = colors.HexColor("#94a3b8")   # slate-400
TEXT_LIGHT = colors.HexColor("#cbd5e1")   # slate-300
CARD_BORDER = colors.HexColor("#1e293b")  # slate-800
CARD_BORDER_ACCENT = colors.HexColor("#334155") # slate-700

PAGE_WIDTH, PAGE_HEIGHT = landscape(letter) # 792 x 612 pt

def draw_wrapped_text(c, text, x, y, max_width, line_height, font_name="MainFont", font_size=10, max_lines=None):
    """Рисует текст с переносом ТОЛЬКО по целым словам."""
    c.setFont(font_name, font_size)
    words = text.split()
    lines = []
    current_line = []
    for word in words:
        test_line = " ".join(current_line + [word])
        if pdfmetrics.stringWidth(test_line, font_name, font_size) <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
                current_line = [word]
            else:
                lines.append(word)
                current_line = []
    if current_line:
        lines.append(" ".join(current_line))
        
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        if lines:
            lines[-1] = lines[-1].rstrip("., ") + "..."
            
    cur_y = y
    for line in lines:
        c.drawString(x, cur_y, line)
        cur_y -= line_height
    return cur_y

def draw_badge(c, x, y, text, bg_color=PRIMARY, text_color=TEXT_WHITE, font_name="BoldFont", font_size=8, pad_x=8, pad_y=4, radius=4):
    """Рисует аккуратную плашку с динамической шириной по тексту."""
    c.setFont(font_name, font_size)
    txt_w = pdfmetrics.stringWidth(text, font_name, font_size)
    badge_w = txt_w + pad_x * 2
    badge_h = font_size + pad_y * 2
    
    c.setFillColor(bg_color)
    c.roundRect(x, y - pad_y, badge_w, badge_h, radius, fill=True, stroke=False)
    
    c.setFillColor(text_color)
    c.drawString(x + pad_x, y, text)
    return badge_w, badge_h

def draw_header(c, slide_num, total_slides, title, category="SANAU.AI • PITCH DECK"):
    # Верхняя неоновая полоса
    c.setFillColor(PRIMARY)
    c.rect(0, PAGE_HEIGHT - 6, PAGE_WIDTH, 6, fill=True, stroke=False)
    
    # Категория
    c.setFont("BoldFont", 9.5)
    c.setFillColor(ACCENT_CYAN)
    c.drawString(40, PAGE_HEIGHT - 34, category.upper())
    
    # Заголовок слайда
    c.setFont("BoldFont", 20)
    c.setFillColor(TEXT_WHITE)
    c.drawString(40, PAGE_HEIGHT - 60, title)
    
    # Разделитель
    c.setStrokeColor(CARD_BORDER_ACCENT)
    c.setLineWidth(1)
    c.line(40, PAGE_HEIGHT - 72, PAGE_WIDTH - 40, PAGE_HEIGHT - 72)
    
    # Нижний колонтитул
    c.setFont("MainFont", 9)
    c.setFillColor(TEXT_MUTED)
    c.drawString(40, 24, "Sanau.AI — Мультимодальный AI-товаровед & Радар маржи")
    c.drawRightString(PAGE_WIDTH - 40, 24, f"Слайд {slide_num} из {total_slides}")

def draw_card(c, x, y, w, h, bg_color=CARD_DARK, border_color=CARD_BORDER, radius=8):
    c.setFillColor(bg_color)
    c.setStrokeColor(border_color)
    c.setLineWidth(1.2)
    c.roundRect(x, y, w, h, radius, fill=True, stroke=True)

# -------------------------------------------------------------
# СЛАЙД 1: Титульный слайд
# -------------------------------------------------------------
def slide_1(c):
    c.setFillColor(BG_DARK)
    c.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=True, stroke=False)
    
    # Декоративный бейдж
    draw_badge(c, 40, PAGE_HEIGHT - 105, "RETAIL TECH • AI FOR LOCAL BUSINESS • ЖАМБЫЛ", 
               bg_color=colors.HexColor("#1e1b4b"), text_color=ACCENT_CYAN, font_size=9, pad_x=10, pad_y=5, radius=5)
    
    # Главный логотип / заголовок
    c.setFont("BoldFont", 44)
    c.setFillColor(TEXT_WHITE)
    c.drawString(40, PAGE_HEIGHT - 165, "Sanau.AI")
    
    # QR-код на титульном слайде
    qr_path = Path(__file__).resolve().parent / "static" / "qr_bot.png"
    if qr_path.exists():
        card_x = PAGE_WIDTH - 175
        card_y = PAGE_HEIGHT - 175
        draw_card(c, card_x, card_y, 135, 140, bg_color=CARD_DARK, border_color=PRIMARY)
        c.drawImage(str(qr_path), card_x + 15, card_y + 30, 105, 105, preserveAspectRatio=True)
        c.setFont("BoldFont", 8.5)
        c.setFillColor(ACCENT_CYAN)
        c.drawCentredString(card_x + 67, card_y + 14, "@Sanau_AI_bot")
    
    # Подзаголовок
    c.setFont("BoldFont", 18)
    c.setFillColor(ACCENT_CYAN)
    c.drawString(40, PAGE_HEIGHT - 200, "Мультимодальный AI-товаровед и радар защиты маржи")
    
    # Теглайн
    c.setFont("MainFont", 13.5)
    c.setFillColor(TEXT_LIGHT)
    c.drawString(40, PAGE_HEIGHT - 230, "От бумажного чека и живого голоса на складе — до автоматической 1С и прибыли за 2 секунды")
    
    # 3 Ключевых метрики
    card_w = (PAGE_WIDTH - 80 - 30) / 3
    metrics = [
        ("2 секунды", "Скорость оцифровки", "Фото чека, накладной или голос на казахском и русском языках", ACCENT_CYAN),
        ("+12–15%", "Защищенная маржа", "Радар на лету выявляет скрытое подорожание товаров поставщиками", ACCENT_GREEN),
        ("1 клик", "Сквозной учет", "Синхронизация в Google Sheets, 1С, Kaspi Pay и базу данных", PRIMARY_LIGHT)
    ]
    
    for i, (val, title, desc, col) in enumerate(metrics):
        x = 40 + i * (card_w + 15)
        y = 115
        draw_card(c, x, y, card_w, 155, border_color=CARD_BORDER_ACCENT)
        
        c.setFont("BoldFont", 22)
        c.setFillColor(col)
        c.drawString(x + 18, y + 115, val)
        
        c.setFont("BoldFont", 13)
        c.setFillColor(TEXT_WHITE)
        c.drawString(x + 18, y + 88, title)
        
        c.setFillColor(TEXT_MUTED)
        draw_wrapped_text(c, desc, x + 18, y + 62, card_w - 36, 16, font_name="MainFont", font_size=10)

    # Футер
    c.setFont("MainFont", 9.5)
    c.setFillColor(TEXT_MUTED)
    c.drawString(40, 45, "Проект: Sanau.AI • Работает 24/7 в Telegram: @Sanau_AI_bot • г. Тараз, 2026")

# -------------------------------------------------------------
# СЛАЙД 2: Проблема и боль рынка
# -------------------------------------------------------------
def slide_2(c):
    c.setFillColor(BG_DARK)
    c.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=True, stroke=False)
    draw_header(c, 2, 10, "Боль региона: Почему магазины у дома теряют миллионы?", "01 / РЫНОЧНАЯ БОЛЬ")
    
    c.setFont("MainFont", 12)
    c.setFillColor(TEXT_WHITE)
    c.drawString(40, PAGE_HEIGHT - 100, "В Казахстане свыше 160 000 торговых точек МСБ (15 000+ в Жамбылской области).")
    c.setFillColor(TEXT_MUTED)
    c.drawString(40, PAGE_HEIGHT - 118, "Каждый магазин принимает 20–40 накладных в неделю. 90% не имеют ПК на складе.")
    
    card_w = (PAGE_WIDTH - 80 - 30) / 3
    cards = [
        ("Скрытый рост оптовых цен", 
         "Поставщик тихо поднимает цену на 8–15% мелким шрифтом на чеке. Хозяин не успевает пересчитать розницу на полке и неделями торгует в минус.",
         "Потери: 150 000 – 350 000 тг/мес", ACCENT_ROSE, colors.HexColor("#2d151e")),
        ("Рутинный ад накладных", 
         "20–40 накладных в неделю вбиваются вручную в тетрадь или Excel. Ошибки в артикулах, потерянные чеки, путаница с остатками и пересортица.",
         "Потери: 15–20 часов рутины/нед", ACCENT_CYAN, colors.HexColor("#14253d")),
        ("Барьер перехода на 1С / ERP", 
         "Тяжелый софт требует ПК, лицензий и долгого обучения персонала. 80% приемщиков общаются только на казахском и русском в Telegram.",
         "Барьер: 70% МСБ бросают ERP", ACCENT_AMBER, colors.HexColor("#2d2013"))
    ]
    
    for i, (title, desc, loss, col, box_bg) in enumerate(cards):
        x = 40 + i * (card_w + 15)
        y = 105
        draw_card(c, x, y, card_w, 320)
        
        # Индикатор карточки
        c.setFillColor(col)
        c.roundRect(x + 18, y + 276, 26, 26, 6, fill=True, stroke=False)
        c.setFont("BoldFont", 12)
        c.setFillColor(TEXT_WHITE)
        c.drawCentredString(x + 31, y + 284, str(i + 1))
        
        c.setFont("BoldFont", 13)
        c.setFillColor(col)
        c.drawString(x + 52, y + 283, title)
        
        # Текст описания с защитой от переносов
        c.setFillColor(TEXT_LIGHT)
        draw_wrapped_text(c, desc, x + 18, y + 245, card_w - 36, 17, font_name="MainFont", font_size=10.5)
            
        # Блок ущерба (гарантированно умещается внутри карточки)
        draw_card(c, x + 14, y + 18, card_w - 28, 44, bg_color=box_bg, border_color=col)
        c.setFont("BoldFont", 9.5)
        c.setFillColor(col)
        c.drawCentredString(x + card_w / 2, y + 36, loss)

# -------------------------------------------------------------
# СЛАЙД 3: Решение Sanau.AI
# -------------------------------------------------------------
def slide_3(c):
    c.setFillColor(BG_DARK)
    c.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=True, stroke=False)
    draw_header(c, 3, 10, "Решение: AI-товаровед в кармане без сложного софта", "02 / ПРОДУКТОВОЕ РЕШЕНИЕ")
    
    c.setFont("MainFont", 12)
    c.setFillColor(TEXT_MUTED)
    c.drawString(40, PAGE_HEIGHT - 100, "Sanau.AI работает прямо внутри Telegram (Bot + Mini App). Ноль обучения персонала, запуск за 1 минуту.")
    
    card_w = (PAGE_WIDTH - 80 - 30) / 3
    features = [
        ("Фото накладной", "Компьютерное зрение GPT-4o-mini", 
         "Сфотографируйте бумажный чек или накладную с камеры смартфона. Нейросеть извлекает товары, количество, цены закупа и суммы за 2.5 сек.",
         "Скорость: ~2.5 сек", ACCENT_CYAN),
        ("Голосовая приемка", "Whisper-1 + NLP (Казахский & Русский)", 
         "Приемщик на складе говорит: «20 сүт Родина 440 теңгеден келді». ИИ понимает разговорный казахский и русский язык без командных шаблонов.",
         "Руки свободны на складе", PRIMARY_LIGHT),
        ("Умный текстовый ввод", "Мультиязычный NLP парсер", 
         "Скопируйте сообщение поставщика из WhatsApp в произвольном виде. Система вычленит позиции и цены за 0.5 секунды без ошибок.",
         "Парсинг: ~0.5 сек", ACCENT_GREEN)
    ]
    
    for i, (title, tech, desc, speed, col) in enumerate(features):
        x = 40 + i * (card_w + 15)
        y = 110
        draw_card(c, x, y, card_w, 310)
        
        # Плашка типа
        draw_badge(c, x + 18, y + 275, title.upper(), bg_color=colors.HexColor("#1e293b"), text_color=TEXT_WHITE, font_size=10, pad_x=8, pad_y=4)
        
        c.setFont("BoldFont", 9.5)
        c.setFillColor(col)
        c.drawString(x + 18, y + 250, tech)
        
        c.setFillColor(TEXT_LIGHT)
        draw_wrapped_text(c, desc, x + 18, y + 225, card_w - 36, 17, font_name="MainFont", font_size=10.5)
            
        # Бейдж скорости
        draw_card(c, x + 14, y + 20, card_w - 28, 38, bg_color=colors.HexColor("#162338"), border_color=col)
        c.setFont("BoldFont", 9.5)
        c.setFillColor(col)
        c.drawCentredString(x + card_w / 2, y + 34, speed)

# -------------------------------------------------------------
# СЛАЙД 4: Киллер-фича — Радар маржи
# -------------------------------------------------------------
def slide_4(c):
    c.setFillColor(BG_DARK)
    c.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=True, stroke=False)
    draw_header(c, 4, 10, "Киллер-фича: «Радар маржи» (Price Spike Radar)", "03 / ТЕХНОЛОГИЧЕСКОЕ ЯДРО")
    
    # Левая колонка: описание алгоритма
    left_w = 390
    draw_card(c, 40, 105, left_w, 375)
    
    c.setFont("BoldFont", 14)
    c.setFillColor(TEXT_WHITE)
    c.drawString(58, 448, "Алгоритм защиты прибыли в реальном времени:")
    
    steps = [
        ("1. Сверка с историей закупа:", "Сравнение закупочной цены товара с прошлыми приходами по контрагенту.", ACCENT_CYAN),
        ("2. Фиксация скачка цены (Price Spike):", "Мгновенный сигнал при удорожании хотя бы на 1 тенге (например, +12.8%).", ACCENT_ROSE),
        ("3. Расчет кассового риска (Risk Exposure):", "Умножение разницы цен на объем партии = Точный прогнозируемый убыток.", ACCENT_AMBER),
        ("4. Автоматическая розничная цена:", "Расчет новой цены с гарантией плановой маржи магазина (25%).", ACCENT_GREEN),
        ("5. Моментальный алерт директору:", "Сообщение в Telegram владельцу: смените ценник прямо сейчас!", PRIMARY_LIGHT)
    ]
    
    cur_y = 415
    for title, desc, col in steps:
        c.setFont("BoldFont", 10.5)
        c.setFillColor(col)
        c.drawString(58, cur_y, title)
        cur_y -= 15
        
        c.setFillColor(TEXT_LIGHT)
        cur_y = draw_wrapped_text(c, desc, 58, cur_y, left_w - 36, 14, font_name="MainFont", font_size=9.5)
        cur_y -= 8

    # Правая колонка: живой пример из Тараза
    right_x = 40 + left_w + 18
    right_w = PAGE_WIDTH - 40 - right_x
    draw_card(c, right_x, 105, right_w, 375, bg_color=colors.HexColor("#0d1b2a"), border_color=PRIMARY)
    
    draw_badge(c, right_x + 18, 448, "РЕАЛЬНЫЙ КЕЙС ТАРАЗА", bg_color=colors.HexColor("#881337"), text_color=TEXT_WHITE, font_size=8.5, pad_x=8, pad_y=4)
    
    c.setFont("BoldFont", 15)
    c.setFillColor(TEXT_WHITE)
    c.drawString(right_x + 18, 420, "Молоко «Родина» 3.2% 1л")
    
    case_rows = [
        ("Старый закуп:", "390 тг", TEXT_WHITE),
        ("Новый закуп в накладной:", "440 тг (+12.8%)", ACCENT_ROSE),
        ("Объем поставки:", "20 шт", TEXT_WHITE),
        ("Прямой риск убытка:", "-1 000 тг на партии", ACCENT_ROSE),
        ("Старая цена на полке:", "490 тг (маржа упала до 10%)", TEXT_MUTED),
        ("Новая цена от Sanau.AI:", "570 тг (маржа 25% спасена)", ACCENT_GREEN)
    ]
    
    cur_y = 385
    for label, val, val_col in case_rows:
        c.setFont("MainFont", 10)
        c.setFillColor(TEXT_MUTED)
        c.drawString(right_x + 18, cur_y, label)
        
        c.setFont("BoldFont", 10)
        c.setFillColor(val_col)
        c.drawString(right_x + 18, cur_y - 14, val)
        cur_y -= 34
        
    draw_card(c, right_x + 14, 118, right_w - 28, 56, bg_color=colors.HexColor("#064e3b"), border_color=ACCENT_GREEN)
    c.setFont("BoldFont", 10.5)
    c.setFillColor(TEXT_WHITE)
    c.drawString(right_x + 24, 154, "ИТОГ РАБОТЫ РАДАРА:")
    c.setFont("MainFont", 9.5)
    c.setFillColor(colors.HexColor("#a7f3d0"))
    c.drawString(right_x + 24, 134, "Магазин сохранил 1 000 тг на одной накладной!")

# -------------------------------------------------------------
# СЛАЙД 5: Сквозная интеграция (Integration Hub)
# -------------------------------------------------------------
def slide_5(c):
    c.setFillColor(BG_DARK)
    c.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=True, stroke=False)
    draw_header(c, 5, 10, "Сквозная синхронизация: Данные сразу во всех сервисах", "04 / ЭКОСИСТЕМА")
    
    c.setFont("MainFont", 12)
    c.setFillColor(TEXT_MUTED)
    c.drawString(40, PAGE_HEIGHT - 100, "Sanau.AI не заставляет менять софт. Мы автоматически наполняем привычные системы данными за 1 клик.")
    
    card_w = (PAGE_WIDTH - 80 - 18) / 2
    card_h = 168
    
    integrations = [
        ("Google Таблицы (Google Sheets)", "Онлайн-запись строк через Webhook",
         "Автоматическое добавление строк прихода в Google Таблицу через Google Apps Script. Подсветка подорожания красным цветом. Готово к работе за 2 минуты.", 40, 275, ACCENT_GREEN),
        ("1С:Предприятие & МойСклад", "REST Webhook + XML CommerceML 2.0",
         "Передача структурированного JSON 'ПриходнаяНакладная' в учетную систему 1С по API или файловая выгрузка по стандарту CommerceML 2.0 (XML).", 40 + card_w + 18, 275, ACCENT_CYAN),
        ("Kaspi Pay / Kaspi Магазин", "Прайс-лист и фид номенклатуры",
         "Генерация актуального каталога с обновленными розничными ценами для моментального обновления цен в кабинете Kaspi Pay.", 40, 95, ACCENT_ROSE),
        ("Telegram Alerts & SQL База", "Мгновенные алерты директору + БД",
         "Личные уведомления владельцу в Telegram при росте цен. Постоянное ведение базы контрагентов и аналитики цен в реляционной SQL БД.", 40 + card_w + 18, 95, PRIMARY_LIGHT)
    ]
    
    for title, sub, desc, x, y, col in integrations:
        draw_card(c, x, y, card_w, card_h)
        
        c.setFont("BoldFont", 13.5)
        c.setFillColor(TEXT_WHITE)
        c.drawString(x + 18, y + 135, title)
        
        c.setFont("BoldFont", 9.5)
        c.setFillColor(col)
        c.drawString(x + 18, y + 116, sub)
        
        c.setFillColor(TEXT_LIGHT)
        draw_wrapped_text(c, desc, x + 18, y + 92, card_w - 36, 17, font_name="MainFont", font_size=10)

# -------------------------------------------------------------
# СЛАЙД 6: Объем рынка (TAM / SAM / SOM)
# -------------------------------------------------------------
def slide_6(c):
    c.setFillColor(BG_DARK)
    c.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=True, stroke=False)
    draw_header(c, 6, 10, "Рыночный потенциал: Огромный неохваченный сегмент МСБ", "05 / ОБЪЕМ РЫНКА")
    
    card_w = (PAGE_WIDTH - 80 - 30) / 3
    tiers = [
        ("TAM: ОБЩИЙ РЫНОК", "$63 000 000 / год", "350 000+ торговых точек",
         "Все точки розничной торговли и HoReCa Казахстана, Узбекистана и Кыргызстана. Магазины у дома, пекарни, аптеки, кафе.", ACCENT_CYAN),
        ("SAM: ДОСТУПНЫЙ РЫНОК", "$28 800 000 / год", "160 000 магазинов у дома",
         "Малый продуктовый и хозяйственный ритейл Казахстана, принимающий накладные вручную и страдающий от инфляции поставщиков.", PRIMARY_LIGHT),
        ("SOM: СТАРТОВЫЙ РЫНОК (1-2 ГОД)", "$320 000 / год (ARR)", "1 500 торговых точек",
         "Жамбылская область (15 000 точек в Таразе и районах) + Южные регионы (Шымкент, Туркестан). 10% проникновения на старте.", ACCENT_GREEN)
    ]
    
    for i, (title, money, qty, desc, color) in enumerate(tiers):
        x = 40 + i * (card_w + 15)
        y = 105
        draw_card(c, x, y, card_w, 365)
        
        draw_badge(c, x + 18, y + 332, title, bg_color=colors.HexColor("#1e293b"), text_color=color, font_size=8.5, pad_x=8, pad_y=4)
        
        c.setFont("BoldFont", 21)
        c.setFillColor(TEXT_WHITE)
        c.drawString(x + 18, y + 295, money)
        
        c.setFont("BoldFont", 11.5)
        c.setFillColor(color)
        c.drawString(x + 18, y + 270, qty)
        
        c.setFillColor(TEXT_LIGHT)
        draw_wrapped_text(c, desc, x + 18, y + 235, card_w - 36, 18, font_name="MainFont", font_size=10.5)
            
        draw_card(c, x + 14, y + 20, card_w - 28, 46, bg_color=colors.HexColor("#111e33"))
        c.setFont("BoldFont", 9)
        c.setFillColor(TEXT_MUTED)
        c.drawCentredString(x + card_w / 2, y + 46, "Средний чек:")
        c.setFont("BoldFont", 10.5)
        c.setFillColor(ACCENT_GREEN)
        c.drawCentredString(x + card_w / 2, y + 30, "15 000 тг в месяц / точка")

# -------------------------------------------------------------
# СЛАЙД 7: Бизнес-модель и Финансовый план
# -------------------------------------------------------------
def slide_7(c):
    c.setFillColor(BG_DARK)
    c.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=True, stroke=False)
    draw_header(c, 7, 10, "Бизнес-модель: B2B SaaS с моментальной окупаемостью", "06 / МОНЕТИЗАЦИЯ И ЭКОНОМИКА")
    
    card_w = (PAGE_WIDTH - 80 - 30) / 3
    tariffs = [
        ("Базовый (Starter)", "7 990 тг / мес", 
         ["До 50 накладных в месяц", "Telegram бот & Mini App", "Радар цен поставщиков", "Синхронизация Google Таблиц", "Текстовый и фото ввод"], False),
        ("Бизнес (Pro)", "14 990 тг / мес", 
         ["Безлимит накладных", "Голосовая приемка (KZ & RU)", "Шлюз 1C / ERP Webhook", "Экспорт Kaspi XML фида", "Telegram алерты директору", "Персонализация магазина"], True),
        ("Сеть (Enterprise)", "39 990 тг / мес", 
         ["Мульти-склад до 5 точек", "Сводная аналитика сети", "Выделенный менеджер", "Прямая интеграция с 1С", "Приоритетная обработка AI"], False)
    ]
    
    for i, (name, price, bullet_list, is_hit) in enumerate(tariffs):
        x = 40 + i * (card_w + 15)
        y = 105
        border = PRIMARY_LIGHT if is_hit else CARD_BORDER
        draw_card(c, x, y, card_w, 365, border_color=border)
        
        # Заголовок тарифа
        c.setFont("BoldFont", 13.5)
        c.setFillColor(TEXT_WHITE)
        c.drawString(x + 18, y + 332, name)
        
        if is_hit:
            draw_badge(c, x + card_w - 62, y + 332, "ХИТ", bg_color=PRIMARY, text_color=TEXT_WHITE, font_size=8, pad_x=6, pad_y=3)
            
        c.setFont("BoldFont", 20)
        c.setFillColor(ACCENT_GREEN if is_hit else ACCENT_CYAN)
        c.drawString(x + 18, y + 295, price)
        
        cur_y = y + 255
        for b in bullet_list:
            c.setFont("BoldFont", 9)
            c.setFillColor(ACCENT_GREEN)
            c.drawString(x + 18, cur_y, "•")
            c.setFont("MainFont", 10)
            c.setFillColor(TEXT_LIGHT)
            c.drawString(x + 30, cur_y, b)
            cur_y -= 25
            
        # Блок окупаемости
        draw_card(c, x + 14, y + 16, card_w - 28, 44, bg_color=colors.HexColor("#14253d"))
        c.setFont("BoldFont", 8.5)
        c.setFillColor(ACCENT_CYAN)
        c.drawCentredString(x + card_w / 2, y + 42, "Окупаемость для магазина:")
        c.setFont("BoldFont", 9.5)
        c.setFillColor(TEXT_WHITE)
        c.drawCentredString(x + card_w / 2, y + 26, "2-3 дня за счет спасения маржи")

# -------------------------------------------------------------
# СЛАЙД 8: Конкурентные преимущества
# -------------------------------------------------------------
def slide_8(c):
    c.setFillColor(BG_DARK)
    c.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=True, stroke=False)
    draw_header(c, 8, 10, "Конкурентные преимущества: Почему выбирают Sanau.AI?", "07 / СРАВНЕНИЕ")
    
    table_x = 40
    table_y = 110
    table_w = PAGE_WIDTH - 80
    table_h = 360
    draw_card(c, table_x, table_y, table_w, table_h)
    
    # Сбалансированная ширина колонок без вылезания
    cols = [
        ("Критерий оценки", 170),
        ("Тетрадь / Excel", 125),
        ("1С / ERP", 125),
        ("Обычные OCR", 125),
        ("Sanau.AI", 167)
    ]
    
    # Шапка таблицы
    cur_x = table_x
    c.setFillColor(colors.HexColor("#1e293b"))
    c.rect(table_x, table_y + table_h - 44, table_w, 44, fill=True, stroke=False)
    
    for name, w in cols:
        c.setFont("BoldFont", 10.5)
        c.setFillColor(ACCENT_GREEN if "Sanau" in name else TEXT_WHITE)
        c.drawString(cur_x + 12, table_y + table_h - 27, name)
        cur_x += w
        
    rows = [
        ("Входной порог", "Низкий", "Очень высокий (ПК)", "Средний", "0 (в Telegram на телефоне)"),
        ("Голос на казахском/русском", "Нет", "Нет", "Нет", "Да (Whisper + NLP)"),
        ("Радар маржи (скачки цен)", "Нет (потери)", "Сложные отчеты", "Только текст", "Автоматически 100%"),
        ("Скорость обработки", "15–30 минут", "10–20 минут", "3–5 минут", "2–3 секунды"),
        ("Интеграция с сервисами", "Нет", "Своя экосистема", "Ограничено", "Google, 1C, Kaspi, SQL"),
        ("Стоимость внедрения", "0 тг (но убытки)", "От 200 000 тг + спец", "От $20 / мес", "От 7 990 тг / мес")
    ]
    
    cur_y = table_y + table_h - 78
    for row_idx, r in enumerate(rows):
        cur_x = table_x
        if row_idx % 2 == 1:
            c.setFillColor(colors.HexColor("#111c2e"))
            c.rect(table_x, cur_y - 8, table_w, 36, fill=True, stroke=False)
            
        for col_idx, text in enumerate(r):
            w = cols[col_idx][1]
            c.setFont("BoldFont" if col_idx == 4 or col_idx == 0 else "MainFont", 9.5)
            if col_idx == 4:
                c.setFillColor(ACCENT_GREEN)
            elif text == "Нет" or "Нет (" in text:
                c.setFillColor(ACCENT_ROSE)
            else:
                c.setFillColor(TEXT_MUTED if col_idx > 0 else TEXT_WHITE)
            c.drawString(cur_x + 12, cur_y + 8, text)
            cur_x += w
            
        cur_y -= 44

# -------------------------------------------------------------
# СЛАЙД 9: Дорожная карта (Roadmap)
# -------------------------------------------------------------
def slide_9(c):
    c.setFillColor(BG_DARK)
    c.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=True, stroke=False)
    draw_header(c, 9, 10, "Дорожная карта: От Тараза до национального масштаба", "08 / СТРАТЕГИЯ РОСТА")
    
    card_w = (PAGE_WIDTH - 80 - 45) / 4
    quarters = [
        ("Q4 2026: Запуск MVP", "г. Тараз", 
         ["Пилот с 50 магазинами", "База поставщиков Тараза", "Telegram бот & Mini App", "Радар цен и Google Sheets"], ACCENT_CYAN),
        ("Q1 2027: Экосистема", "Интеграции", 
         ["Коннектор Kaspi Pay QR", "Шлюз Webkassa / re:Kassa", "Печать ценников Bluetooth", "Мобильный сканер штрихкодов"], PRIMARY_LIGHT),
        ("Q2 2027: Экспансия", "Юг Казахстана", 
         ["Шымкент, Туркестан, Алматы", "1 500+ платящих точек", "Партнерство с оптовиками", "ARR: $250 000+"], ACCENT_GREEN),
        ("Q3-Q4 2027: AI-Supply", "Автозаказ", 
         ["Прогноз дефицита остатков", "Автоформирование заказа", "Финтех-скоринг ритейлеров", "Рынок Узбекистана"], ACCENT_AMBER)
    ]
    
    for i, (q, sub, items, color) in enumerate(quarters):
        x = 40 + i * (card_w + 15)
        y = 110
        draw_card(c, x, y, card_w, 355)
        
        # Шапка квартала
        draw_badge(c, x + 14, y + 312, q, bg_color=color, text_color=TEXT_WHITE, font_size=9, pad_x=8, pad_y=4)
        
        c.setFont("BoldFont", 11)
        c.setFillColor(TEXT_MUTED)
        c.drawString(x + 14, y + 288, sub)
        
        cur_y = y + 245
        for it in items:
            c.setFont("BoldFont", 9)
            c.setFillColor(color)
            c.drawString(x + 14, cur_y, "•")
            
            c.setFillColor(TEXT_LIGHT)
            cur_y = draw_wrapped_text(c, it, x + 24, cur_y, card_w - 34, 15, font_name="MainFont", font_size=9.5)
            cur_y -= 8

# -------------------------------------------------------------
# СЛАЙД 10: Команда и Призыв к действию
# -------------------------------------------------------------
def slide_10(c):
    c.setFillColor(BG_DARK)
    c.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=True, stroke=False)
    draw_header(c, 10, 10, "Sanau.AI: Готовы к внедрению в магазины уже сегодня", "09 / LIVE DEMO & КОНТАКТЫ")
    
    # Левая колонка: статус готовности
    left_w = 385
    draw_card(c, 40, 105, left_w, 370)
    
    c.setFont("BoldFont", 15)
    c.setFillColor(TEXT_WHITE)
    c.drawString(60, 442, "Текущий статус продукта:")
    
    bullets = [
        ("Рабочий MVP 24/7 в облаке Railway:", "https://sanauai-production.up.railway.app"),
        ("Telegram-бот в продакшене:", "@Sanau_AI_bot (принимает аудио, фото и текст)"),
        ("Интеграции работают онлайн:", "Google Таблицы, 1C REST Webhook, XML экспорт"),
        ("Протестировано на ценах Тараза:", "Реальные товары местных поставщиков (Родина, Цесна)"),
        ("Защита маржи в реальном времени:", "Авторасчет наценки и предупреждение о скрытом росте")
    ]
    
    cur_y = 405
    for title, desc in bullets:
        c.setFont("BoldFont", 10.5)
        c.setFillColor(ACCENT_GREEN)
        c.drawString(60, cur_y, f"• {title}")
        cur_y -= 15
        
        c.setFont("MainFont", 9.5)
        c.setFillColor(TEXT_LIGHT)
        cur_y = draw_wrapped_text(c, desc, 74, cur_y, left_w - 90, 14, font_name="MainFont", font_size=9.5)
        cur_y -= 10

    # Правая колонка: призыв к действию и QR-код
    right_x = 40 + left_w + 18
    right_w = PAGE_WIDTH - 40 - right_x
    draw_card(c, right_x, 105, right_w, 370, bg_color=colors.HexColor("#0d1b2a"), border_color=PRIMARY)
    
    c.setFont("BoldFont", 15)
    c.setFillColor(TEXT_WHITE)
    c.drawString(right_x + 18, 442, "Попробуйте прямо сейчас!")
    
    c.setFont("MainFont", 10)
    c.setFillColor(TEXT_MUTED)
    c.drawString(right_x + 18, 422, "Отсканируйте камерой смартфона:")

    qr_path = Path(__file__).resolve().parent / "static" / "qr_bot.png"
    if qr_path.exists():
        qr_card_w = 130
        draw_card(c, right_x + 18, 255, qr_card_w, 150, bg_color=CARD_DARK, border_color=ACCENT_CYAN)
        c.drawImage(str(qr_path), right_x + 25, 275, 116, 116, preserveAspectRatio=True)
        c.setFont("BoldFont", 9)
        c.setFillColor(TEXT_WHITE)
        c.drawCentredString(right_x + 18 + qr_card_w / 2, 263, "@Sanau_AI_bot")
        
    # Справа от QR-кода
    c.setFont("BoldFont", 12)
    c.setFillColor(ACCENT_GREEN)
    c.drawString(right_x + 162, 375, "Telegram Bot")
    
    c.setFont("MainFont", 9.5)
    c.setFillColor(TEXT_LIGHT)
    c.drawString(right_x + 162, 350, "• Приемка по фото")
    c.drawString(right_x + 162, 330, "• Голос KZ / RU")
    c.drawString(right_x + 162, 310, "• Радар маржи")
    c.drawString(right_x + 162, 290, "• Доступ 24/7")

    # Контакты внизу карточки
    draw_card(c, right_x + 18, 120, right_w - 36, 115, bg_color=colors.HexColor("#111e33"))
    c.setFont("BoldFont", 10.5)
    c.setFillColor(TEXT_WHITE)
    c.drawString(right_x + 30, 208, "Контакты и ресурсы:")
    c.setFont("MainFont", 9.5)
    c.setFillColor(TEXT_LIGHT)
    c.drawString(right_x + 30, 188, "Бот: @Sanau_AI_bot")
    c.drawString(right_x + 30, 168, "GitHub: github.com/Almerek999/Sanau.AI")
    c.drawString(right_x + 30, 148, "Локация: г. Тараз, Казахстан")
    c.drawString(right_x + 30, 128, "Хакатон: Цифровой Жамбыл 2026")

def generate_pdf(output_path="presentation_pitch_deck.pdf"):
    c = canvas.Canvas(output_path, pagesize=landscape(letter))
    c.setTitle("Sanau.AI Pitch Deck")
    c.setAuthor("Sanau.AI Team")
    
    slides = [
        slide_1, slide_2, slide_3, slide_4, slide_5,
        slide_6, slide_7, slide_8, slide_9, slide_10
    ]
    
    for i, slide_fn in enumerate(slides):
        slide_fn(c)
        c.showPage()
        
    c.save()
    print(f"✅ ПДФ Презентация успешно создана: {output_path}")

if __name__ == "__main__":
    out = "presentation_pitch_deck.pdf"
    if len(sys.argv) > 1:
        out = sys.argv[1]
    generate_pdf(out)
