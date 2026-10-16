import streamlit as st
import pandas as pd
import json
import time
import io
from PIL import Image

from database.db import init_db, get_connection
from database.seed_data import seed
from services.ai_engine import process_invoice, get_demo_sample_invoice
from services.radar import analyze_invoice_pricing
from services.connectors.manager import IntegrationManager
from demo_assets.sample_invoices import generate_invoice_image, SAMPLE_VOICE_TRANSCRIPTS
import config

# Настройка страницы
st.set_page_config(
    page_title="Sanau.AI — Товаровед & Радар маржи",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Инициализация БД при первом запуске
if "db_initialized" not in st.session_state:
    init_db()
    seed()
    st.session_state.db_initialized = True

# Состояние приложения
if "current_invoice" not in st.session_state:
    st.session_state.current_invoice = None
if "sync_results" not in st.session_state:
    st.session_state.sync_results = []

# Пользовательский CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 18px;
        text-align: center;
    }
    .alert-card-danger {
        background: linear-gradient(135deg, #FFF1F2 0%, #FFE4E6 100%);
        border-left: 5px solid #E11D48;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 12px;
    }
    .alert-card-success {
        background: linear-gradient(135deg, #F0FDF4 0%, #DCFCE7 100%);
        border-left: 5px solid #16A34A;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 12px;
    }
    .badge-kazakhstan {
        background-color: #0284C7;
        color: white;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-hub {
        background-color: #D97706;
        color: white;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- САЙДБАР: НАСТРОЙКИ ИНТЕГРАЦИЙ -----------------
st.sidebar.markdown("### ⚙️ Настройки интеграций")
st.sidebar.caption("Жюри может указать свои сервисы:")

# Интеграция 1: Google Sheets
st.sidebar.markdown("#### 📊 Google Sheets")
google_enabled = st.sidebar.checkbox("Включить Google Sheets", value=True)
google_url = st.sidebar.text_input(
    "Webhook URL таблицы",
    value="",
    placeholder="https://script.google.com/macros/s/...",
    help="URL вебхука Google Apps Script / SheetDB"
)

# Интеграция 2: Telegram Notifier
st.sidebar.markdown("#### ✈️ Telegram Алерты")
tg_enabled = st.sidebar.checkbox("Включить Telegram-отчеты", value=True)
tg_token = st.sidebar.text_input(
    "Bot Token",
    value=config.TELEGRAM_BOT_TOKEN,
    type="password",
    placeholder="123456:ABC-DEF..."
)
tg_chat_id = st.sidebar.text_input(
    "Ваш Chat ID (для жюри)",
    value=config.TELEGRAM_DEFAULT_CHAT_ID,
    placeholder="Например: 589218321"
)

# Интеграция 3: 1C / ERP Webhook
st.sidebar.markdown("#### 🏢 1C / ERP Webhook")
webhook_enabled = st.sidebar.checkbox("Включить 1C/ERP Webhook", value=True)
webhook_url = st.sidebar.text_input(
    "URL REST Webhook",
    value=config.DEFAULT_WEBHOOK_URL or "https://webhook.site/demo-sanau",
    placeholder="https://webhook.site/your-unique-id"
)

# Интеграция 4: SQL Database
st.sidebar.markdown("#### 🗄️ SQL База данных")
sql_enabled = st.sidebar.checkbox("Включить запись в SQL DB", value=True)

# Инициализируем менеджер интеграций с текущими настройками
integration_cfg = {
    "sql_enabled": sql_enabled,
    "google_enabled": google_enabled,
    "google_sheets_url": google_url,
    "telegram_enabled": tg_enabled,
    "telegram_token": tg_token,
    "telegram_chat_id": tg_chat_id,
    "webhook_enabled": webhook_enabled,
    "webhook_url": webhook_url
}
manager = IntegrationManager(integration_cfg)

st.sidebar.markdown("---")
# Кнопка проверки всех коннекторов
if st.sidebar.button("🔍 Проверить связь со всеми сервисами", use_container_width=True):
    with st.sidebar:
        test_results = manager.test_all()
        for r in test_results:
            if r.success:
                st.success(f"**{r.connector_name}**: ✅ {r.message}")
            else:
                st.warning(f"**{r.connector_name}**: ⚠️ {r.message}")

# Кнопка сброса базы на демо-данные
if st.sidebar.button("🔄 Сбросить базу на демо-данные Тараза"):
    seed()
    st.sidebar.success("Каталог и поставщики восстановлены!")

# API ключ Gemini
st.sidebar.markdown("---")
gemini_key_input = st.sidebar.text_input(
    "Google Gemini API Key (Опционально)",
    value=config.GEMINI_API_KEY,
    type="password",
    help="Если ключ не указан, работает встроенный офлайн AI-генератор"
)

# ----------------- ШАПКА ПРИЛОЖЕНИЯ -----------------
col_title, col_badges = st.columns([3, 1])
with col_title:
    st.markdown('<div class="main-header">📦 Sanau.AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">AI-товаровед, распознавание накладных и радар защиты маржи для МСБ Жамбылской области</div>', unsafe_allow_html=True)
with col_badges:
    st.markdown("""
    <div style="text-align: right; padding-top: 10px;">
        <span class="badge-hub">Zhambyl Hub Hackathon</span><br><br>
        <span class="badge-kazakhstan">г. Тараз • МСБ / ШОБ</span>
    </div>
    """, unsafe_allow_html=True)

# ----------------- ВКЛАДКИ ПРИЛОЖЕНИЯ -----------------
tab_demo, tab_integrations, tab_radar, tab_database = st.tabs([
    "📸 1. Приемка товара (Live Demo)",
    "🔌 2. Интеграции & Журнал синхронизации",
    "📈 3. Финансовый радар цен",
    "🗄️ 4. База данных & Экспорт в 1C/Excel"
])

# =========================================================================
# ВКЛАДКА 1: ПРИЕМКА ТОВАРА (LIVE DEMO)
# =========================================================================
with tab_demo:
    col_input, col_result = st.columns([1, 1], gap="medium")
    
    with col_input:
        st.markdown("### 📥 Способ ввода данных")
        input_mode = st.radio(
            "Выберите источник накладной:",
            [
                "⚡ Готовый демо-сценарий (Для стабильного питча)",
                "📷 Загрузить реальное фото / скан накладной",
                "🎙️ Голосовая приемка (Казахский / Русский)"
            ],
            horizontal=False
        )
        
        uploaded_image_bytes = None
        voice_text_input = None
        selected_sample_id = None
        
        if "Готовый демо-сценарий" in input_mode:
            scenario = st.selectbox(
                "Выберите кейс для демонстрации жюри:",
                [
                    "🚨 Кейс 1: ТОО 'Прима' (Скрытый рост цен на Молоко Родина и Муку Цесна)",
                    "🎙️ Кейс 2: ИП 'Ахметов' (Голосовая приемка на казахском со склада Аулие-Ата)",
                    "✅ Кейс 3: ТОО 'RG Brands' (Штатная поставка: вода Tassay, чай Пиала)"
                ]
            )
            
            if "Кейс 1" in scenario:
                selected_sample_id = "spike_milk_flour"
                preview_img_bytes = generate_invoice_image(
                    invoice_number="KZ-7841/Т",
                    supplier="ТОО 'Прима Дистрибьюшн Тараз'",
                    date="2026-10-12"
                )
                st.image(preview_img_bytes, caption="Накладная поставщика (обратите внимание на Молоко и Муку)", use_container_width=True)
            elif "Кейс 2" in scenario:
                selected_sample_id = "kazakh_voice"
                st.info(f"🗣️ **Аудиозапись приемщика на казахском языке:**\n\n*«{SAMPLE_VOICE_TRANSCRIPTS['kaz_1']}»*")
            else:
                selected_sample_id = "stable_rg"
                st.info("📦 **Поставка напитков и чая:** стабильные контрактные цены без подорожания.")
                
        elif "Загрузить реальное фото" in input_mode:
            uploaded_file = st.file_uploader("Загрузите фото бумажной накладной (PNG, JPG)", type=["png", "jpg", "jpeg"])
            if uploaded_file:
                uploaded_image_bytes = uploaded_file.read()
                st.image(uploaded_image_bytes, caption="Загруженная накладная", use_container_width=True)
            else:
                st.caption("Или сгенерируйте тестовый бланк:")
                if st.button("Сгенерировать бланк накладной Тараза"):
                    uploaded_image_bytes = generate_invoice_image()
                    st.image(uploaded_image_bytes, caption="Сгенерированная накладная", use_container_width=True)
                    
        elif "Голосовая приемка" in input_mode:
            st.markdown("Введите или выберите голосовую фразу приемщика:")
            sample_voice_key = st.selectbox(
                "Быстрый выбор голосового образца:",
                [
                    "Аулие-Ата (Казахский): Шедевр, қант, күріш",
                    "Прима (Русский): Молоко Родина, мука Цесна",
                    "Эмиль (Казахский): Сүт, сыр Президент"
                ]
            )
            if "Аулие-Ата" in sample_voice_key:
                default_voice = SAMPLE_VOICE_TRANSCRIPTS["kaz_1"]
            elif "Прима" in sample_voice_key:
                default_voice = SAMPLE_VOICE_TRANSCRIPTS["rus_1"]
            else:
                default_voice = SAMPLE_VOICE_TRANSCRIPTS["kaz_2"]
                
            voice_text_input = st.text_area("Транскрипт голосового сообщения:", value=default_voice, height=100)
            st.caption("💡 В реальном Telegram/WhatsApp боте продавец нажимает кнопку микрофона и диктует вслух.")
            
        process_btn = st.button("🚀 Распознать и проанализировать маржу", type="primary", use_container_width=True)
        if process_btn:
            with st.spinner("AI анализирует документ, сопоставляет номенклатуру и сверяет цены..."):
                time.sleep(0.6)  # Эффект обработки
                res = process_invoice(
                    image_bytes=uploaded_image_bytes,
                    voice_text=voice_text_input,
                    sample_id=selected_sample_id,
                    api_key=gemini_key_input
                )
                st.session_state.current_invoice = res
                st.session_state.sync_results = []
                st.success("Обработка завершена!")
                
    # Правая колонка: Результаты распознавания и радар
    with col_result:
        st.markdown("### 📊 Результат анализа")
        inv = st.session_state.current_invoice
        
        if not inv:
            st.info("👈 Нажмите кнопку **«Распознать и проанализировать маржу»**, чтобы запустить AI-движок.")
        else:
            # Шапка накладной
            st.markdown(f"""
            **Накладная:** `{inv.get('invoice_number')}` | **Дата:** `{inv.get('date')}`  
            **Поставщик:** **{inv.get('supplier_name')}**  
            **Общая сумма закупки:** <span style="font-size: 1.2rem; font-weight: bold; color: #0284C7;">{inv.get('total_amount', 0):,.0f} ₸</span>
            """, unsafe_allow_html=True)
            
            # Алерты подорожания
            spikes = inv.get("spikes_count", 0)
            loss = inv.get("total_potential_loss_kzt", 0)
            
            if spikes > 0:
                st.markdown(f"""
                <div class="alert-card-danger">
                    <strong style="color: #9F1239; font-size: 1.1rem;">🚨 РАДАР МАРЖИ: Обнаружен рост цен ({spikes} поз.)!</strong><br>
                    Поставщик поднял закупочные цены. Если оставить старые цены на полке, магазин потеряет 
                    <strong>{loss:,.0f} ₸</strong> чистой прибыли на этой партии!
                </div>
                """.replace(",", " "), unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="alert-card-success">
                    <strong style="color: #14532D; font-size: 1.05rem;">✅ Все цены стабильны</strong><br>
                    Закупочные цены соответствуют контракту. Маржинальность сохранена.
                </div>
                """, unsafe_allow_html=True)
                
            # Таблица распознанных позиций
            items = inv.get("items", [])
            df_display = []
            for it in items:
                status_text = "ОК"
                if it.get("is_price_increase"):
                    status_text = f"🚨 +{it.get('price_change_pct')}%"
                    
                df_display.append({
                    "Товар": it.get("product_name"),
                    "Кол-во": f"{it.get('quantity')} {it.get('unit')}",
                    "Закупка нов. (₸)": f"{it.get('purchase_price'):,.0f}".replace(",", " "),
                    "Закупка стар. (₸)": f"{it.get('previous_price', 0):,.0f}".replace(",", " ") if it.get("previous_price") else "-",
                    "Динамика": status_text,
                    "Реком. розница (₸)": f"{it.get('recommended_retail_price', 0):,.0f}".replace(",", " "),
                    "Сумма (₸)": f"{it.get('total_price'):,.0f}".replace(",", " ")
                })
            st.dataframe(pd.DataFrame(df_display), use_container_width=True, hide_index=True)
            
            # ----------------- КНОПКА СИНХРОНИЗАЦИИ ВО ВСЕ СЕРВИСЫ -----------------
            st.markdown("---")
            st.markdown("#### ⚡ Действие: Внесение данных в сервисы")
            sync_btn = st.button("💾 Подтвердить приемку и занести во ВСЕ подключенные сервисы", type="primary", use_container_width=True)
            
            if sync_btn:
                with st.spinner("Идет синхронизация: запись в Google Sheets, отправка в Telegram, 1C Webhook и SQL..."):
                    results = manager.sync_to_all(inv)
                    st.session_state.sync_results = results
                    st.toast("Данные успешно разнесены по подключенным сервисам!", icon="✅")
                    
            # Отображение результатов синхронизации
            if st.session_state.sync_results:
                st.markdown("##### Статус отправки по подключенным сервисам:")
                for r in st.session_state.sync_results:
                    if r.success:
                        st.success(f"**{r.connector_name}** ({r.target}): {r.message} (синхронизировано строк: {r.records_synced})")
                    else:
                        st.error(f"**{r.connector_name}** ({r.target}): ❌ {r.message}")

# =========================================================================
# ВКЛАДКА 2: ИНТЕГРАЦИИ & ЖУРНАЛ СИНХРОНИЗАЦИИ
# =========================================================================
with tab_demo:
    pass

with tab_integrations:
    st.markdown("### 🔌 Подключенные сервисы и базы данных")
    st.markdown("Любой предприниматель или член жюри может подключить свою систему учета за 30 секунд:")
    
    col_s1, col_s2 = st.columns(2)
    
    with col_s1:
        st.markdown("#### 1. 📊 Google Таблицы (Online Spreadsheet)")
        st.write("""
        - **Как это работает:** ИИ в реальном времени добавляет строки прихода с колонками даты, товара, количества, закупочной цены и предупреждения о росте цен.
        - **Ссылка на вебхук:** Задается в панели слева.
        - **Демо-таблица:** Если свой вебхук еще не создан, система использует встроенный виртуальный стрим строк.
        """)
        if st.button("🧪 Тест Google Sheets Webhook"):
            res = manager.google_conn.test_connection()
            if res.success:
                st.success(res.message)
            else:
                st.warning(res.message)
                
        st.markdown("---")
        st.markdown("#### 2. ✈️ Telegram Бот (Уведомления владельца и бухгалтера)")
        st.write("""
        - **Как это работает:** Владелец магазина или управляющий моментально получает в Telegram сводку каждой накладной и красный алерт с рекомендованной ценой для кассира.
        - **Проверка:** Введите ваш Telegram Chat ID в сайдбаре слева.
        """)
        if st.button("🧪 Отправить тестовое сообщение в Telegram"):
            res = manager.tg_conn.test_connection()
            if res.success:
                st.success(res.message)
            else:
                st.error(res.message)
                
    with col_s2:
        st.markdown("#### 3. 🏢 1C:Предприятие / МойСклад / ERP Webhook")
        st.write("""
        - **Как это работает:** Отправка структурированного JSON стандарта REST API на любой указанный URL.
        - **Формат:** Содержит `invoice_number`, `supplier`, `inventory_lines`, `price_delta_pct`.
        """)
        if st.button("🧪 Отправить тестовый Ping на 1C/ERP Webhook"):
            res = manager.webhook_conn.test_connection()
            if res.success:
                st.success(res.message)
            else:
                st.error(res.message)
                
        st.markdown("---")
        st.markdown("#### 4. 🗄️ SQL База данных (SQLite / PostgreSQL)")
        st.write("""
        - **Как это работает:** Прямая транзакционная запись в таблицы `invoices` и `invoice_items` с автоматическим обновлением текущей стоимости товара в каталоге.
        """)
        if st.button("🧪 Проверить связь с базой данных SQL"):
            res = manager.sql_conn.test_connection()
            if res.success:
                st.success(res.message)
            else:
                st.error(res.message)
                
    st.markdown("---")
    st.markdown("### 📋 Sync Audit Log (Журнал фактических отправок)")
    st.caption("Фиксация всех вызовов внешних сервисов с кодами ответа:")
    recent_logs = IntegrationManager.get_recent_logs(limit=10)
    if recent_logs:
        df_logs = pd.DataFrame(recent_logs)
        df_logs.columns = ["Сервис", "Куда отправлено", "Статус", "Строк", "Ответ сервера / Описание", "Время"]
        st.dataframe(df_logs, use_container_width=True, hide_index=True)
    else:
        st.info("Журнал пока пуст. Проведите первую приемку во вкладке «Приемка товара».")

# =========================================================================
# ВКЛАДКА 3: ФИНАНСОВЫЙ РАДАР ЦЕН
# =========================================================================
with tab_radar:
    st.markdown("### 📈 Аналитика цен и защита маржинальности магазина")
    st.caption("Анализ поведения поставщиков в Таразе за последний период:")
    
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.markdown("""
        <div class="metric-card">
            <div style="font-size: 0.85rem; color: #64748B;">Принято накладных</div>
            <div style="font-size: 1.8rem; font-weight: bold; color: #0284C7;">18</div>
        </div>
        """, unsafe_allow_html=True)
    with col_m2:
        st.markdown("""
        <div class="metric-card">
            <div style="font-size: 0.85rem; color: #64748B;">Общий оборот закупа</div>
            <div style="font-size: 1.8rem; font-weight: bold; color: #1E293B;">642 800 ₸</div>
        </div>
        """, unsafe_allow_html=True)
    with col_m3:
        st.markdown("""
        <div class="metric-card">
            <div style="font-size: 0.85rem; color: #64748B;">Позиций с ростом цен</div>
            <div style="font-size: 1.8rem; font-weight: bold; color: #E11D48;">4 товара</div>
        </div>
        """, unsafe_allow_html=True)
    with col_m4:
        st.markdown("""
        <div class="metric-card">
            <div style="font-size: 0.85rem; color: #64748B;">Спасенная маржа (ROI)</div>
            <div style="font-size: 1.8rem; font-weight: bold; color: #16A34A;">+38 400 ₸</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("---")
    st.markdown("#### 🚨 Товары в зоне риска (Недавние подорожания у поставщиков Тараза)")
    
    radar_data = [
        {"Товар": "Молоко 'Родина' 3.2% 1л", "Поставщик": "ТОО 'Прима Дистрибьюшн'", "Старая цена": 390, "Новая цена": 440, "Рост": "+12.8%", "Текущая розница": 480, "Реком. розница": 550, "Потеря маржи": "18.7% ➔ 8.3%"},
        {"Товар": "Мука пшеничная 'Цесна' 2кг", "Поставщик": "ТОО 'Прима Дистрибьюшн'", "Старая цена": 680, "Новая цена": 760, "Рост": "+11.7%", "Текущая розница": 850, "Реком. розница": 950, "Потеря маржи": "25.0% ➔ 10.5%"},
        {"Товар": "Масло растительное 'Шедевр' 1л", "Поставщик": "ИП 'Ахметов' (Аулие-Ата)", "Старая цена": 750, "Новая цена": 840, "Рост": "+12.0%", "Текущая розница": 920, "Реком. розница": 1050, "Потеря маржи": "22.6% ➔ 8.7%"},
        {"Товар": "Сыр 'President' Сливочный 200г", "Поставщик": "ТОО 'Эмиль'", "Старая цена": 1100, "Новая цена": 1250, "Рост": "+13.6%", "Текущая розница": 1450, "Реком. розница": 1560, "Потеря маржи": "31.8% ➔ 13.8%"},
    ]
    st.dataframe(pd.DataFrame(radar_data), use_container_width=True, hide_index=True)

# =========================================================================
# ВКЛАДКА 4: БАЗА ДАННЫХ И ЭКСПОРТ
# =========================================================================
with tab_database:
    st.markdown("### 🗄️ База данных магазина и экспорт")
    
    conn = get_connection()
    df_products = pd.read_sql_query("SELECT id, name, category, unit, current_purchase_price, recommended_retail_price, target_margin_pct, updated_at FROM products", conn)
    df_invoices = pd.read_sql_query("SELECT id, invoice_number, supplier_name, date, total_amount, status, created_at FROM invoices ORDER BY id DESC", conn)
    conn.close()
    
    st.markdown("#### 📦 Каталог товаров магазина (Справочник цен)")
    st.dataframe(df_products, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    st.markdown("#### 📥 Экспорт данных")
    col_e1, col_e2, col_e3 = st.columns(3)
    
    with col_e1:
        # Excel экспорт
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            df_products.to_excel(writer, sheet_name="Номенклатура", index=False)
            df_invoices.to_excel(writer, sheet_name="Накладные", index=False)
        st.download_button(
            label="📥 Скачать каталог в Excel (.xlsx)",
            data=excel_buffer.getvalue(),
            file_name="sanau_catalog_taraz.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
    with col_e2:
        # XML экспорт для 1C
        xml_data = f"""<?xml version="1.0" encoding="UTF-8"?>
<КоммерческаяИнформация ВерсияСхемы="2.09" ДатаФормирования="{time.strftime('%Y-%m-%d')}">
  <Каталог СодержитТовары="true">
    <Ид>SANAU-TARAZ-001</Ид>
    <Наименование>Основной каталог Sanau.AI Тараз</Наименование>
    <Товары>
"""
        for _, row in df_products.iterrows():
            xml_data += f"""      <Товар>
        <Ид>{row['id']}</Ид>
        <Наименование>{row['name']}</Наименование>
        <БазоваяЕдиница>{row['unit']}</БазоваяЕдиница>
        <ЦенаЗакупки>{row['current_purchase_price']}</ЦенаЗакупки>
        <ЦенаПродажи>{row['recommended_retail_price']}</ЦенаПродажи>
      </Товар>\n"""
        xml_data += """    </Товары>
  </Каталог>
</КоммерческаяИнформация>"""
        st.download_button(
            label="📥 Скачать XML для 1C:Предприятие 8.3",
            data=xml_data,
            file_name="sanau_1c_exchange.xml",
            mime="application/xml",
            use_container_width=True
        )
        
    with col_e3:
        # CSV для Kaspi Pay / Kaspi Магазина
        kaspi_csv = df_products[["name", "recommended_retail_price"]].copy()
        kaspi_csv.columns = ["model", "price"]
        kaspi_csv["availabilities"] = "yes"
        csv_buffer = kaspi_csv.to_csv(index=False, sep=";").encode("utf-8")
        st.download_button(
            label="📥 Скачать фид для Kaspi Pay/Магазина (.csv)",
            data=csv_buffer,
            file_name="kaspi_feed_taraz.csv",
            mime="text/csv",
            use_container_width=True
        )
