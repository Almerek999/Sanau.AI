import os
import sys
from pathlib import Path
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Регистрация кириллических шрифтов
FONT_PATH = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_BOLD_PATH = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"

pdfmetrics.registerFont(TTFont("Arial", FONT_PATH))
pdfmetrics.registerFont(TTFont("Arial-Bold", FONT_BOLD_PATH))

# Цветовая палитра
BG_DARK = colors.HexColor("#0f172a")      # slate-900
CARD_DARK = colors.HexColor("#1e293b")    # slate-800
PRIMARY = colors.HexColor("#4f46e5")      # indigo-600
ACCENT_SKY = colors.HexColor("#0284c7")   # sky-600
ACCENT_GREEN = colors.HexColor("#059669") # emerald-600
ACCENT_ROSE = colors.HexColor("#e11d48")  # rose-600
TEXT_WHITE = colors.HexColor("#ffffff")
TEXT_MUTED = colors.HexColor("#94a3b8")   # slate-400
TEXT_DARK = colors.HexColor("#1e293b")
BG_LIGHT = colors.HexColor("#f8fafc")     # slate-50
CARD_BORDER = colors.HexColor("#334155")  # slate-700

PAGE_WIDTH, PAGE_HEIGHT = landscape(letter) # 792 x 612 pt

def draw_header(c, slide_num, total_slides, title, category="SANAU.AI • PITCH DECK"):
    # Верхняя полоса
    c.setFillColor(PRIMARY)
    c.rect(0, PAGE_HEIGHT - 6, PAGE_WIDTH, 6, fill=True, stroke=False)
    
    # Категория
    c.setFont("Arial-Bold", 10)
    c.setFillColor(ACCENT_SKY)
    c.drawString(40, PAGE_HEIGHT - 35, category.upper())
    
    # Заголовок слайда
    c.setFont("Arial-Bold", 22)
    c.setFillColor(TEXT_WHITE)
    c.drawString(40, PAGE_HEIGHT - 62, title)
    
    # Разделитель
    c.setStrokeColor(CARD_BORDER)
    c.setLineWidth(1)
    c.line(40, PAGE_HEIGHT - 75, PAGE_WIDTH - 40, PAGE_HEIGHT - 75)
    
    # Нижний колонтитул
    c.setFont("Arial", 9)
    c.setFillColor(TEXT_MUTED)
    c.drawString(40, 25, "Sanau.AI — AI-товаровед & Радар маржи для МСБ")
    c.drawRightString(PAGE_WIDTH - 40, 25, f"Слайд {slide_num} из {total_slides}")

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
    
    # Декоративный градиент-блок
    c.setFillColor(PRIMARY)
    c.roundRect(40, PAGE_HEIGHT - 120, 160, 28, 6, fill=True, stroke=False)
    c.setFont("Arial-Bold", 11)
    c.setFillColor(TEXT_WHITE)
    c.drawString(55, PAGE_HEIGHT - 102, "RETAIL TECH • AI FOR SME")
    
    # Главный логотип / заголовок
    c.setFont("Arial-Bold", 46)
    c.setFillColor(TEXT_WHITE)
    c.drawString(40, PAGE_HEIGHT - 180, "Sanau.AI 📦⚡")
    
    # QR-код на титульном слайде
    qr_path = Path(__file__).resolve().parent / "static" / "qr_bot.png"
    if qr_path.exists():
        draw_card(c, PAGE_WIDTH - 170, PAGE_HEIGHT - 175, 130, 135, bg_color=CARD_DARK, border_color=PRIMARY)
        c.drawImage(str(qr_path), PAGE_WIDTH - 158, PAGE_HEIGHT - 145, 105, 105, preserveAspectRatio=True)
        c.setFont("Arial-Bold", 8)
        c.setFillColor(TEXT_WHITE)
        c.drawCentredString(PAGE_WIDTH - 105, PAGE_HEIGHT - 163, "SCAN @Sanau_AI_bot")
    
    # Подзаголовок
    c.setFont("Arial-Bold", 20)
    c.setFillColor(ACCENT_SKY)
    c.drawString(40, PAGE_HEIGHT - 215, "Мультимодальный AI-товаровед и радар защиты маржи")
    
    # Теглайн
    c.setFont("Arial", 15)
    c.setFillColor(TEXT_MUTED)
    c.drawString(40, PAGE_HEIGHT - 250, "От бумажного чека и голоса — до автоматической 1С и сбереженной прибыли за 3 секунды")
    
    # 3 Ключевых метрики
    card_w = (PAGE_WIDTH - 80 - 30) / 3
    metrics = [
        ("2 секунды", "Скорость оцифровки", "Фото чека, накладной или голос на казахском/русском"),
        ("+12-15%", "Защищенная маржа", "Радар моментально фиксирует скрытое подорожание"),
        ("1 клик", "Синхронизация", "Онлайн-выгрузка в Google Sheets, 1С, Kaspi и базу данных")
    ]
    
    for i, (val, title, desc) in enumerate(metrics):
        x = 40 + i * (card_w + 15)
        y = 120
        draw_card(c, x, y, card_w, 150)
        
        c.setFont("Arial-Bold", 24)
        c.setFillColor(ACCENT_GREEN if i == 1 else ACCENT_SKY)
        c.drawString(x + 20, y + 105, val)
        
        c.setFont("Arial-Bold", 13)
        c.setFillColor(TEXT_WHITE)
        c.drawString(x + 20, y + 80, title)
        
        c.setFont("Arial", 10)
        c.setFillColor(TEXT_MUTED)
        # перенос строк для описания
        c.drawString(x + 20, y + 55, desc[:36])
        if len(desc) > 36:
            c.drawString(x + 20, y + 40, desc[36:])

    # Футер
    c.setFont("Arial", 10)
    c.setFillColor(TEXT_MUTED)
    c.drawString(40, 45, "Проект: Sanau.AI • Работает 24/7 в Telegram: @Sanau_AI_bot")

# -------------------------------------------------------------
# СЛАЙД 2: Проблема и боль рынка
# -------------------------------------------------------------
def slide_2(c):
    c.setFillColor(BG_DARK)
    c.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=True, stroke=False)
    draw_header(c, 2, 10, "Боль региона: Почему магазины у дома теряют миллионы?", "РЫНОЧНАЯ ПРОБЛЕМА")
    
    # Введение
    c.setFont("Arial", 13)
    c.setFillColor(TEXT_WHITE)
    c.drawString(40, PAGE_HEIGHT - 105, "В регионах Казахстана свыше 160 000 торговых точек МСБ (15 000+ в Жамбылской области).")
    c.setFillColor(TEXT_MUTED)
    c.drawString(40, PAGE_HEIGHT - 125, "Каждый магазин принимает 20–40 накладных в неделю. 90% учета ведется вручную или в тетрадях.")
    
    card_w = (PAGE_WIDTH - 80 - 30) / 3
    cards = [
        ("🚨 1. Скрытый рост цен", 
         "Поставщик тихо поднимает цену на 8–15%. Товаровед не успевает пересчитать ценник на полке. Магазин неделями продает товар в минус или в ноль.",
         "Потери: 150 000 – 350 000 ₸ в месяц"),
        ("⏳ 2. Рутинный ад накладных", 
         "Приемщик вручную вбивает 40 позиций с мятого чека в тетрадь или 1С. Это занимает 15–20 часов в неделю, порождает массу человеческих ошибок.",
         "Потери: 80+ часов рутины в месяц"),
        ("🛑 3. Технический барьер", 
         "Традиционные 1С и ERP слишком сложны, требуют ПК и дорогого обучения. 80% приемщиков общаются только в Telegram/WhatsApp на казахском и русском.",
         "Барьер: 70% МСБ отказываются от ERP")
    ]
    
    for i, (title, desc, loss) in enumerate(cards):
        x = 40 + i * (card_w + 15)
        y = 110
        draw_card(c, x, y, card_w, 310)
        
        c.setFont("Arial-Bold", 14)
        c.setFillColor(ACCENT_ROSE if i == 0 else (ACCENT_SKY if i == 1 else colors.HexColor("#f59e0b")))
        c.drawString(x + 18, y + 270, title)
        
        # Текст описания
        c.setFont("Arial", 11)
        c.setFillColor(TEXT_MUTED)
        words = desc.split(" ")
        line = ""
        cur_y = y + 235
        for w in words:
            if len(line + " " + w) < 32:
                line = (line + " " + w).strip()
            else:
                c.drawString(x + 18, cur_y, line)
                cur_y -= 18
                line = w
        if line:
            c.drawString(x + 18, cur_y, line)
            
        # Блок ущерба
        draw_card(c, x + 15, y + 20, card_w - 30, 48, bg_color=colors.HexColor("#2d151e" if i == 0 else "#14253d"))
        c.setFont("Arial-Bold", 10)
        c.setFillColor(ACCENT_ROSE if i == 0 else ACCENT_SKY)
        c.drawString(x + 25, y + 40, loss)

# -------------------------------------------------------------
# СЛАЙД 3: Решение Sanau.AI
# -------------------------------------------------------------
def slide_3(c):
    c.setFillColor(BG_DARK)
    c.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=True, stroke=False)
    draw_header(c, 3, 10, "Решение: AI-товаровед в кармане без сложного софта", "ПРОДУКТОВОЕ РЕШЕНИЕ")
    
    c.setFont("Arial", 13)
    c.setFillColor(TEXT_MUTED)
    c.drawString(40, PAGE_HEIGHT - 105, "Sanau.AI работает прямо внутри Telegram (Bot + Mini App). Ноль обучения персонала.")
    
    # 3 Способа ввода
    card_w = (PAGE_WIDTH - 80 - 30) / 3
    features = [
        ("📸 Фото накладной", "Компьютерное зрение GPT-4o-mini", 
         "Сфотографируйте бумажный чек или накладную прямо с камеры смартфона. Нейросеть мгновенно извлекает товары, количество, цены закупа и суммы."),
        ("🎙️ Голосовая приемка", "Whisper-1 + NLP (KZ & RU)", 
         "Приемщик на складе просто говорит: «20 сүт Родина 440 теңгеден келді». ИИ понимает разговорный казахский и русский язык без командных шаблонов."),
        ("✍️ Свободный текст", "Мультиязычный парсер", 
         "Скопируйте сообщение поставщика из WhatsApp в произвольном виде. Система вычленит позиции и цены за 0.5 секунды без ошибок.")
    ]
    
    for i, (title, tech, desc) in enumerate(features):
        x = 40 + i * (card_w + 15)
        y = 120
        draw_card(c, x, y, card_w, 290)
        
        c.setFont("Arial-Bold", 16)
        c.setFillColor(TEXT_WHITE)
        c.drawString(x + 18, y + 250, title)
        
        c.setFont("Arial-Bold", 10)
        c.setFillColor(ACCENT_SKY)
        c.drawString(x + 18, y + 230, tech)
        
        c.setFont("Arial", 11)
        c.setFillColor(TEXT_MUTED)
        words = desc.split(" ")
        line = ""
        cur_y = y + 195
        for w in words:
            if len(line + " " + w) < 32:
                line = (line + " " + w).strip()
            else:
                c.drawString(x + 18, cur_y, line)
                cur_y -= 18
                line = w
        if line:
            c.drawString(x + 18, cur_y, line)
            
        # Бейдж скорости
        c.setFillColor(colors.HexColor("#1e3a5f"))
        c.roundRect(x + 18, y + 25, 120, 26, 4, fill=True, stroke=False)
        c.setFont("Arial-Bold", 9)
        c.setFillColor(ACCENT_SKY)
        c.drawString(x + 28, y + 36, "⚡ Время: ~2 сек")

# -------------------------------------------------------------
# СЛАЙД 4: Киллер-фича — Радар маржи
# -------------------------------------------------------------
def slide_4(c):
    c.setFillColor(BG_DARK)
    c.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=True, stroke=False)
    draw_header(c, 4, 10, "Киллер-фича: «Радар маржи» (Price Spike Radar)", "ИНТЕЛЛЕКТУАЛЬНОЕ ЯДРО")
    
    # Левая колонка: описание алгоритма
    left_w = (PAGE_WIDTH - 80) * 0.52
    draw_card(c, 40, 110, left_w, 370)
    
    c.setFont("Arial-Bold", 15)
    c.setFillColor(TEXT_WHITE)
    c.drawString(60, 445, "Как Радар защищает прибыль магазина:")
    
    steps = [
        ("1. Сверка с историей закупа:", "Каждая позиция мгновенно проверяется по базе предыдущих поставок конкретного поставщика."),
        ("2. Фиксация скачка цены (Price Spike):", "Если закуп вырос хотя бы на 1 тенге, товар подсвечивается красным статусом (например, +12.8%)."),
        ("3. Расчет кассового риска (Risk Exposure):", "ИИ считает точный убыток: Рост цены x Количество в партии = Убыток при старой рознице."),
        ("4. Автоматический пересчет розницы:", "С учетом целевой маржи магазина (25%) система сразу выдает новую цену на полку (например: 570 ₸)."),
        ("5. Моментальный алерт директору:", "Сообщение в Telegram владельцу: «Подорожало Молоко Родина, смените ценник!»")
    ]
    
    cur_y = 410
    for title, desc in steps:
        c.setFont("Arial-Bold", 11)
        c.setFillColor(ACCENT_SKY)
        c.drawString(60, cur_y, title)
        cur_y -= 16
        c.setFont("Arial", 10)
        c.setFillColor(TEXT_MUTED)
        c.drawString(60, cur_y, desc[:58])
        if len(desc) > 58:
            cur_y -= 14
            c.drawString(60, cur_y, desc[58:])
        cur_y -= 20

    # Правая колонка: наглядный живой пример
    right_x = 40 + left_w + 20
    right_w = PAGE_WIDTH - 40 - right_x
    draw_card(c, right_x, 110, right_w, 370, bg_color=colors.HexColor("#162338"))
    
    c.setFont("Arial-Bold", 14)
    c.setFillColor(ACCENT_ROSE)
    c.drawString(right_x + 20, 445, "🚨 РЕАЛЬНЫЙ КЕЙС ТАРАЗА:")
    
    c.setFont("Arial-Bold", 16)
    c.setFillColor(TEXT_WHITE)
    c.drawString(right_x + 20, 415, "Молоко «Родина» 3.2% 1л")
    
    case_rows = [
        ("Старая цена закупа:", "390 ₸"),
        ("Новая цена в накладной:", "440 ₸ (+12.8%)"),
        ("Объем поставки:", "20 шт"),
        ("Прямой риск убытка:", "-1 000 ₸ на 1 накладной"),
        ("Старая цена на полке:", "490 ₸ (маржа упала до 10%)"),
        ("Новая цена от Sanau.AI:", "570 ₸ (маржа 25% спасена)")
    ]
    
    cur_y = 370
    for label, val in case_rows:
        c.setFont("Arial", 11)
        c.setFillColor(TEXT_MUTED)
        c.drawString(right_x + 20, cur_y, label)
        c.setFont("Arial-Bold", 11)
        c.setFillColor(ACCENT_ROSE if "-" in val or "+" in val else (ACCENT_GREEN if "спасена" in val else TEXT_WHITE))
        c.drawRightString(right_x + right_w - 20, cur_y, val)
        cur_y -= 28
        
    draw_card(c, right_x + 15, 130, right_w - 30, 60, bg_color=colors.HexColor("#064e3b"))
    c.setFont("Arial-Bold", 11)
    c.setFillColor(TEXT_WHITE)
    c.drawString(right_x + 30, 165, "ИТОГ РАБОТЫ РАДАРА:")
    c.setFont("Arial", 10)
    c.setFillColor(colors.HexColor("#a7f3d0"))
    c.drawString(right_x + 30, 145, "Магазин сохранил 1 000 ₸ на одной позиции!")

# -------------------------------------------------------------
# СЛАЙД 5: Сквозная интеграция (Integration Hub)
# -------------------------------------------------------------
def slide_5(c):
    c.setFillColor(BG_DARK)
    c.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=True, stroke=False)
    draw_header(c, 5, 10, "Сквозная синхронизация: Данные сразу во всех сервисах", "ИНТЕГРАЦИОННЫЙ ХАБ")
    
    c.setFont("Arial", 13)
    c.setFillColor(TEXT_MUTED)
    c.drawString(40, PAGE_HEIGHT - 105, "Sanau.AI не заменяет текущий софт магазина, а мгновенно наполняет его данными в 1 клик.")
    
    card_w = (PAGE_WIDTH - 80 - 15) / 2
    card_h = 165
    
    integrations = [
        ("📊 Google Таблицы (Google Sheets)", "Онлайн-запись строк через Webhook",
         "Автоматическое добавление строк прихода в Google Таблицу через Google Apps Script. Подсветка подорожания красным цветом. Готово за 2 минуты.", 40, 275),
        ("🏢 1С:Предприятие & МойСклад", "REST Webhook + XML CommerceML 2.0",
         "Передача структурированного JSON 'ПриходнаяНакладная' в учетную систему 1С по API или файловая выгрузка по стандарту CommerceML 2.0.", 40 + card_w + 15, 275),
        ("💳 Kaspi Pay / Kaspi Магазин", "Прайс-лист и фид номенклатуры",
         "Генерация актуального каталога с обновленными розничными ценами для моментального обновления цен в кабинете Kaspi Pay.", 40, 95),
        ("✈️ Telegram Alerts & SQL База", "Мгновенные алерты директору + БД",
         "Личные уведомления владельцу в Telegram при росте цен. Постоянное ведение базы контрагентов и аналитики цен в реляционной SQL БД.", 40 + card_w + 15, 95)
    ]
    
    for title, sub, desc, x, y in integrations:
        draw_card(c, x, y, card_w, card_h)
        c.setFont("Arial-Bold", 14)
        c.setFillColor(TEXT_WHITE)
        c.drawString(x + 18, y + 130, title)
        
        c.setFont("Arial-Bold", 9.5)
        c.setFillColor(ACCENT_SKY)
        c.drawString(x + 18, y + 112, sub)
        
        c.setFont("Arial", 10.5)
        c.setFillColor(TEXT_MUTED)
        words = desc.split(" ")
        line = ""
        cur_y = y + 85
        for w in words:
            if len(line + " " + w) < 48:
                line = (line + " " + w).strip()
            else:
                c.drawString(x + 18, cur_y, line)
                cur_y -= 16
                line = w
        if line:
            c.drawString(x + 18, cur_y, line)

# -------------------------------------------------------------
# СЛАЙД 6: Объем рынка (TAM / SAM / SOM)
# -------------------------------------------------------------
def slide_6(c):
    c.setFillColor(BG_DARK)
    c.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=True, stroke=False)
    draw_header(c, 6, 10, "Рыночный потенциал: Огромный неохваченный сегмент МСБ", "ОБЪЕМ РЫНКА")
    
    card_w = (PAGE_WIDTH - 80 - 30) / 3
    tiers = [
        ("TAM: Общий рынок", "$63 000 000 / год", "350 000+ торговых точек",
         "Все точки розничной торговли и HoReCa Казахстана, Узбекистана и Кыргызстана. Магазины у дома, пекарни, аптеки, кафе.", ACCENT_SKY),
        ("SAM: Доступный рынок", "$28 800 000 / год", "160 000 магазинов у дома",
         "Малый продуктовый и хозяйственный ритейл Казахстана, принимающий накладные вручную и страдающий от инфляции поставщиков.", PRIMARY),
        ("SOM: Стартовый рынок (1-2 год)", "$320 000 / год (ARR)", "1 500 торговых точек",
         "Жамбылская область (15 000 точек в Таразе и районах) + Южные регионы (Шымкент, Туркестан). 10% проникновения на старте.", ACCENT_GREEN)
    ]
    
    for i, (title, money, qty, desc, color) in enumerate(tiers):
        x = 40 + i * (card_w + 15)
        y = 110
        draw_card(c, x, y, card_w, 360)
        
        c.setFont("Arial-Bold", 14)
        c.setFillColor(color)
        c.drawString(x + 20, y + 320, title)
        
        c.setFont("Arial-Bold", 22)
        c.setFillColor(TEXT_WHITE)
        c.drawString(x + 20, y + 280, money)
        
        c.setFont("Arial-Bold", 12)
        c.setFillColor(ACCENT_SKY)
        c.drawString(x + 20, y + 250, qty)
        
        c.setFont("Arial", 11)
        c.setFillColor(TEXT_MUTED)
        words = desc.split(" ")
        line = ""
        cur_y = y + 200
        for w in words:
            if len(line + " " + w) < 30:
                line = (line + " " + w).strip()
            else:
                c.drawString(x + 20, cur_y, line)
                cur_y -= 18
                line = w
        if line:
            c.drawString(x + 20, cur_y, line)
            
        draw_card(c, x + 15, y + 25, card_w - 30, 50, bg_color=colors.HexColor("#111e33"))
        c.setFont("Arial-Bold", 10)
        c.setFillColor(TEXT_WHITE)
        c.drawString(x + 25, y + 50, "Средний чек:")
        c.setFont("Arial-Bold", 11)
        c.setFillColor(ACCENT_GREEN)
        c.drawString(x + 25, y + 34, "15 000 ₸ в месяц / точка")

# -------------------------------------------------------------
# СЛАЙД 7: Бизнес-модель и Финансовый план
# -------------------------------------------------------------
def slide_7(c):
    c.setFillColor(BG_DARK)
    c.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=True, stroke=False)
    draw_header(c, 7, 10, "Бизнес-модель: B2B SaaS с мгновенной окупаемостью", "МОНЕТИЗАЦИЯ И ЭКОНОМИКА")
    
    # 3 Тарифа
    card_w = (PAGE_WIDTH - 80 - 30) / 3
    tariffs = [
        ("Базовый (Starter)", "7 990 ₸ / мес", 
         ["До 50 накладных в месяц", "Telegram бот & Mini App", "Радар цен поставщиков", "Синхронизация Google Таблиц", "Текстовый и фото ввод"], False),
        ("Бизнес (Pro) • ХИТ", "14 990 ₸ / мес", 
         ["Безлимит накладных", "Голосовая приемка (KZ & RU)", "Шлюз 1C / ERP Webhook", "Экспорт Kaspi XML фида", "Telegram алерты директору", "Персонализация магазина"], True),
        ("Сеть (Enterprise)", "39 990 ₸ / мес", 
         ["Мульти-склад до 5 точек", "Сводная аналитика сети", "Выделенный менеджер", "Прямая интеграция с 1С", "Приоритетная обработка AI"], False)
    ]
    
    for i, (name, price, bullet_list, is_hit) in enumerate(tariffs):
        x = 40 + i * (card_w + 15)
        y = 110
        border = PRIMARY if is_hit else CARD_BORDER
        draw_card(c, x, y, card_w, 360, border_color=border)
        
        if is_hit:
            c.setFillColor(PRIMARY)
            c.roundRect(x + card_w - 95, y + 325, 80, 22, 4, fill=True, stroke=False)
            c.setFont("Arial-Bold", 8)
            c.setFillColor(TEXT_WHITE)
            c.drawString(x + card_w - 85, y + 333, "ПОПУЛЯРНЫЙ")
            
        c.setFont("Arial-Bold", 14)
        c.setFillColor(TEXT_WHITE)
        c.drawString(x + 18, y + 325, name)
        
        c.setFont("Arial-Bold", 20)
        c.setFillColor(ACCENT_GREEN if is_hit else ACCENT_SKY)
        c.drawString(x + 18, y + 290, price)
        
        cur_y = y + 245
        for b in bullet_list:
            c.setFont("Arial-Bold", 10)
            c.setFillColor(ACCENT_GREEN)
            c.drawString(x + 18, cur_y, "✓")
            c.setFont("Arial", 10.5)
            c.setFillColor(TEXT_MUTED)
            c.drawString(x + 32, cur_y, b)
            cur_y -= 26
            
        # Блок окупаемости
        draw_card(c, x + 12, y + 15, card_w - 24, 45, bg_color=colors.HexColor("#14253d"))
        c.setFont("Arial-Bold", 9)
        c.setFillColor(ACCENT_SKY)
        c.drawString(x + 20, y + 35, "Окупаемость для магазина:")
        c.setFont("Arial-Bold", 10)
        c.setFillColor(TEXT_WHITE)
        c.drawString(x + 20, y + 22, "2-3 дня за счет спасения маржи")

# -------------------------------------------------------------
# СЛАЙД 8: Конкурентные преимущества
# -------------------------------------------------------------
def slide_8(c):
    c.setFillColor(BG_DARK)
    c.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=True, stroke=False)
    draw_header(c, 8, 10, "Конкурентные преимущества: Почему выбирают Sanau.AI?", "СРАВНЕНИЕ С АЛЬТЕРНАТИВАМИ")
    
    # Таблица сравнения
    table_x = 40
    table_y = 120
    table_w = PAGE_WIDTH - 80
    table_h = 350
    draw_card(c, table_x, table_y, table_w, table_h)
    
    cols = [
        ("Критерий оценки", 180),
        ("Тетрадь / Ручной", 130),
        ("Тяжелые 1C / ERP", 130),
        ("Обычные сканеры", 130),
        ("Sanau.AI ⚡", 142)
    ]
    
    # Шапка таблицы
    cur_x = table_x
    c.setFillColor(colors.HexColor("#24334a"))
    c.rect(table_x, table_y + table_h - 45, table_w, 45, fill=True, stroke=False)
    
    for name, w in cols:
        c.setFont("Arial-Bold", 11)
        c.setFillColor(ACCENT_GREEN if "Sanau" in name else TEXT_WHITE)
        c.drawString(cur_x + 12, table_y + table_h - 28, name)
        cur_x += w
        
    rows = [
        ("Входной порог", "Очень низкий", "Очень высокий (ПК)", "Средний", "0 (в Telegram на телефоне)"),
        ("Голос на казахском/русском", "❌ Нет", "❌ Нет", "❌ Нет", "✅ Да (Whisper + NLP)"),
        ("Радар маржи (скачки цен)", "❌ Нет (потери)", "⚠️ Сложно настроить", "❌ Только текст", "✅ Автоматически 100%"),
        ("Скорость обработки", "15–30 минут", "10–20 минут", "3–5 минут", "⚡ 2–3 секунды"),
        ("Интеграция с сервисами", "❌ Нет", "Своя экосистема", "Ограничено", "✅ Google, 1C, Kaspi, SQL"),
        ("Стоимость внедрения", "0 ₸", "От 200 000 ₸ + спец", "От $20 / мес", "От 7 990 ₸ / мес")
    ]
    
    cur_y = table_y + table_h - 75
    for row_idx, r in enumerate(rows):
        cur_x = table_x
        # полосатый фон
        if row_idx % 2 == 1:
            c.setFillColor(colors.HexColor("#162338"))
            c.rect(table_x, cur_y - 10, table_w, 36, fill=True, stroke=False)
            
        for col_idx, text in enumerate(r):
            w = cols[col_idx][1]
            c.setFont("Arial-Bold" if col_idx == 4 or col_idx == 0 else "Arial", 10.5)
            if col_idx == 4:
                c.setFillColor(ACCENT_GREEN)
            elif "❌" in text:
                c.setFillColor(ACCENT_ROSE)
            else:
                c.setFillColor(TEXT_MUTED if col_idx > 0 else TEXT_WHITE)
            c.drawString(cur_x + 12, cur_y + 8, text)
            cur_x += w
            
        cur_y -= 42

# -------------------------------------------------------------
# СЛАЙД 9: Дорожная карта (Roadmap)
# -------------------------------------------------------------
def slide_9(c):
    c.setFillColor(BG_DARK)
    c.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=True, stroke=False)
    draw_header(c, 9, 10, "Дорожная карта: От Тараза до национального масштаба", "ПЛАН РАЗВИТИЯ")
    
    card_w = (PAGE_WIDTH - 80 - 45) / 4
    quarters = [
        ("Q4 2026: Запуск MVP", "г. Тараз", 
         ["Пилот с 50 магазинами у дома", "Связка с оптовиками Тараза", "Telegram бот + Mini App 24/7", "Радар маржи и Google Sheets"], ACCENT_SKY),
        ("Q1 2027: Экосистема", "Интеграции", 
         ["Прямой коннектор Kaspi Pay QR", "Интеграция с Webkassa / re:Kassa", "Печать ценников по Bluetooth", "Мобильное сканирование штрихкодов"], PRIMARY),
        ("Q2 2027: Экспансия", "Юг Казахстана", 
         ["Выход в Шымкент, Туркестан, Алматы", "1 500+ активных платящих точек", "Партнерство с дистрибьюторами", "ARR: $250 000+"], ACCENT_GREEN),
        ("Q3-Q4 2027: AI-Supply", "Автозаказ", 
         ["AI-прогноз дефицита остатков", "Автоформирование заказа поставщику", "Финтех-скоринг ритейлеров", "Выход на рынок Узбекистана"], colors.HexColor("#f59e0b"))
    ]
    
    for i, (q, sub, items, color) in enumerate(quarters):
        x = 40 + i * (card_w + 15)
        y = 120
        draw_card(c, x, y, card_w, 340)
        
        # Бейдж квартала
        c.setFillColor(color)
        c.roundRect(x + 15, y + 290, card_w - 30, 28, 4, fill=True, stroke=False)
        c.setFont("Arial-Bold", 10.5)
        c.setFillColor(TEXT_WHITE)
        c.drawCentredString(x + card_w / 2, y + 300, q)
        
        c.setFont("Arial-Bold", 11)
        c.setFillColor(TEXT_MUTED)
        c.drawCentredString(x + card_w / 2, y + 265, sub)
        
        cur_y = y + 225
        for it in items:
            c.setFont("Arial-Bold", 10)
            c.setFillColor(color)
            c.drawString(x + 15, cur_y, "•")
            c.setFont("Arial", 10)
            c.setFillColor(TEXT_WHITE)
            c.drawString(x + 25, cur_y, it[:24])
            if len(it) > 24:
                cur_y -= 14
                c.drawString(x + 25, cur_y, it[24:])
            cur_y -= 24

# -------------------------------------------------------------
# СЛАЙД 10: Команда и Призыв к действию
# -------------------------------------------------------------
def slide_10(c):
    c.setFillColor(BG_DARK)
    c.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=True, stroke=False)
    draw_header(c, 10, 10, "Sanau.AI: Готовы к внедрению в магазины уже сегодня", "КОНТАКТЫ И ДЕМО")
    
    # Левая колонка: статус готовности
    left_w = (PAGE_WIDTH - 80) * 0.55
    draw_card(c, 40, 110, left_w, 360)
    
    c.setFont("Arial-Bold", 16)
    c.setFillColor(TEXT_WHITE)
    c.drawString(65, 430, "Текущий статус продукта:")
    
    bullets = [
        ("✅ Рабочий MVP 24/7 в облаке Railway:", "https://sanauai-production.up.railway.app"),
        ("✅ Telegram-бот в продакшене:", "@Sanau_AI_bot (принимает аудио, фото и текст)"),
        ("✅ Интеграции работают онлайн:", "Google Таблицы, 1C REST Webhook, XML экспорт"),
        ("✅ Протестировано на ценах Тараза:", "Реальные товары местных поставщиков (Родина, Цесна)"),
        ("✅ Защита данных:", "Поддержка работы с локальной базой и API ключами")
    ]
    
    cur_y = 390
    for title, desc in bullets:
        c.setFont("Arial-Bold", 11)
        c.setFillColor(ACCENT_GREEN)
        c.drawString(65, cur_y, title)
        cur_y -= 16
        c.setFont("Arial", 10.5)
        c.setFillColor(TEXT_MUTED)
        c.drawString(65, cur_y, desc)
        cur_y -= 26

    # Правая колонка: призыв к действию и QR-код
    right_x = 40 + left_w + 20
    right_w = PAGE_WIDTH - 40 - right_x
    draw_card(c, right_x, 110, right_w, 360, bg_color=colors.HexColor("#1b2840"), border_color=PRIMARY)
    
    c.setFont("Arial-Bold", 17)
    c.setFillColor(TEXT_WHITE)
    c.drawString(right_x + 20, 430, "Попробуйте прямо сейчас!")
    
    c.setFont("Arial", 10.5)
    c.setFillColor(TEXT_MUTED)
    c.drawString(right_x + 20, 408, "Отсканируйте камерой телефона:")

    qr_path = Path(__file__).resolve().parent / "static" / "qr_bot.png"
    if qr_path.exists():
        draw_card(c, right_x + 20, 240, 140, 150, bg_color=colors.HexColor("#0f172a"), border_color=ACCENT_SKY)
        c.drawImage(str(qr_path), right_x + 27, 260, 125, 125, preserveAspectRatio=True)
        c.setFont("Arial-Bold", 9)
        c.setFillColor(TEXT_WHITE)
        c.drawCentredString(right_x + 90, 248, "@Sanau_AI_bot")
        
    # Справа от QR-кода
    c.setFont("Arial-Bold", 13)
    c.setFillColor(ACCENT_GREEN)
    c.drawString(right_x + 175, 360, "Telegram Bot & App")
    
    c.setFont("Arial", 9.5)
    c.setFillColor(TEXT_MUTED)
    c.drawString(right_x + 175, 335, "• Приемка по фото")
    c.drawString(right_x + 175, 315, "• Голос KZ / RU")
    c.drawString(right_x + 175, 295, "• Радар маржи")
    c.drawString(right_x + 175, 275, "• Доступ 24/7")

    # Контакты внизу карточки
    draw_card(c, right_x + 20, 125, right_w - 40, 95, bg_color=colors.HexColor("#111e33"))
    c.setFont("Arial-Bold", 11)
    c.setFillColor(TEXT_WHITE)
    c.drawString(right_x + 35, 195, "Контакты и ресурсы:")
    c.setFont("Arial", 9.5)
    c.setFillColor(TEXT_MUTED)
    c.drawString(right_x + 35, 175, "🤖 Бот: @Sanau_AI_bot")
    c.drawString(right_x + 35, 155, "🌐 GitHub: github.com/Almerek999/Sanau.AI")
    c.drawString(right_x + 35, 135, "📍 г. Тараз, Казахстан")

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
