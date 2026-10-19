import os
import re
import json
import base64
import requests
from typing import Dict, Any, Optional
from PIL import Image
import io
import config
from services.radar import analyze_invoice_pricing
from database.db import get_setting

# Системный промпт для казахстанских накладных
INVOICE_PARSE_PROMPT = """
Ты — AI-товаровед в Казахстане (город Тараз). Твоя задача — извлечь данные из накладной (фото бумажной накладной, чека, счет-фактуры или рукописной записи).
Учитывай специфику рынка РК:
- Валюта: тенге (KZT / ₸).
- Язык накладной: русский, казахский или смешанный.
- Типичные бренды: Родина, Цесна, Шедевр, Пиала, Баян Сулу, Султан, RG Brands, Прима.

Верни СТРОГО валидный JSON без markdown-оберток (без ```json):
{
  "invoice_number": "номер накладной (строка или 'б/н')",
  "supplier_name": "Название компании или поставщика (например: ТОО 'RG Brands Тараз')",
  "date": "дата в формате ГГГГ-ММ-ДД или как в чеке",
  "items": [
    {
      "product_name": "Название товара (например: Молоко 'Родина' 3.2% 1л)",
      "category": "Категория (Молочная продукция, Бакалея, Напитки и т.д.)",
      "quantity": 10.0,
      "unit": "шт или кг или л",
      "purchase_price": 440.0,
      "total_price": 4400.0
    }
  ]
}
ВАЖНО:
- Поля quantity, purchase_price, total_price ОБЯЗАТЕЛЬНО должны быть числами (float или int), никогда не null.
- Если цена не указана, ставь 0.0. Если количество не указано, ставь 1.0.
"""

VOICE_PARSE_PROMPT = """
Ты — AI-ассистент товароведа в Казахстане. Твоя задача — прослушать или разобрать голосовое сообщение приемщика товара на складе (на казахском или русском языке) и извлечь структурированные данные о принятом товаре.
Обрати особое внимание на казахскую разговорную речь и термины торговли:
- сүт (молоко), май (масло), ұн (мука), қант (сахар), күріш (рис), шай (чай), конфет (конфеты), су (вода).
- өлшем бірліктері: қорап (коробка), бөтелке (бутылка), қап (мешок), дана/пачка (штук).
- баға: "440 теңгеден", "780-нен", "520-дан" означает закупочную цену за 1 единицу.

Верни СТРОГО валидный JSON без markdown-оберток:
{
  "invoice_number": "Голосовая-приемка",
  "supplier_name": "Название поставщика или 'Локальный закуп Тараз'",
  "date": "Сегодня",
  "transcription": "Дословный распознанный текст сказанной речи",
  "items": [
    {
      "product_name": "Название товара",
      "category": "Категория",
      "quantity": 10.0,
      "unit": "шт/кг",
      "purchase_price": 440.0,
      "total_price": 4400.0
    }
  ]
}
ВАЖНО:
- Поля quantity, purchase_price, total_price ОБЯЗАТЕЛЬНО должны быть числами (float или int), НИКОГДА не null и не строки.
- Если цена не названа, ставь purchase_price: 0.0. Если количество не названо, ставь quantity: 1.0.
"""

def clean_json_response(raw_text: str) -> str:
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

def get_active_gemini_key(custom_key: str = "") -> str:
    if custom_key and custom_key.strip() and not custom_key.startswith("sk-"):
        return custom_key.strip()
    db_key = get_setting("gemini_api_key", "").strip()
    if db_key:
        return db_key
    return config.GEMINI_API_KEY.strip()

def get_active_openai_key(custom_key: str = "") -> str:
    if custom_key and custom_key.strip() and custom_key.startswith("sk-"):
        return custom_key.strip()
    db_key = get_setting("openai_api_key", "").strip()
    if db_key:
        return db_key
    return config.OPENAI_API_KEY.strip()

# =========================================================================
# OPENAI REAL IMPLEMENTATION (GPT-4o-mini Vision & Whisper Audio)
# =========================================================================
def parse_invoice_with_openai(image_bytes: bytes, api_key: str = "") -> Optional[Dict[str, Any]]:
    """Парсинг фото накладной через OpenAI GPT-4o-mini Vision"""
    key = get_active_openai_key(api_key)
    if not key:
        return None
    try:
        url = "https://api.openai.com/v1/chat/completions"
        b64_img = base64.b64encode(image_bytes).decode("utf-8")
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": INVOICE_PARSE_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Распознай эту товарную накладную Казахстана и верни структурированный JSON:"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{b64_img}"
                            }
                        }
                    ]
                }
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=25)
        if resp.status_code == 200:
            result_json = resp.json()
            content = result_json["choices"][0]["message"]["content"]
            data = json.loads(clean_json_response(content))
            data["source_type"] = "photo_openai"
            return data
        else:
            print(f"OpenAI Vision Error {resp.status_code}: {resp.text}")
            return None
    except Exception as e:
        print(f"OpenAI Vision error: {e}")
        return None

def parse_voice_audio_bytes_with_openai(audio_bytes: bytes, mime_type: str = "audio/ogg", api_key: str = "") -> Optional[Dict[str, Any]]:
    """Распознавание речи через OpenAI Whisper + структурирование в GPT-4o-mini"""
    key = get_active_openai_key(api_key)
    if not key:
        return None
    try:
        # 1. Whisper transcription
        url_whisper = "https://api.openai.com/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {key}"}
        # Telegram voice files typically have .oga or .ogg extension
        ext = "oga" if ("ogg" in mime_type or "oga" in mime_type) else "wav"
        files = {
            "file": (f"audio.{ext}", io.BytesIO(audio_bytes), mime_type),
            "model": (None, "whisper-1")
        }
        resp = requests.post(url_whisper, headers=headers, files=files, timeout=45)
        if resp.status_code == 401:
            print("OpenAI Whisper Error: 401 Unauthorized (Invalid API Key)")
            return {"error": "API-ключ OpenAI недействителен (401 Unauthorized). Обновите ключ в настройках Mini App или отправьте накладную текстом."}
        if resp.status_code != 200:
            print(f"OpenAI Whisper Error {resp.status_code}: {resp.text}")
            return {"error": f"Сбой сервиса расшифровки речи OpenAI Whisper (HTTP {resp.status_code})."}
            
        transcription = resp.json().get("text", "")
        if not transcription:
            return {"error": "Речь в аудиосообщении не обнаружена. Пожалуйста, повторите четче."}
            
        # 2. GPT-4o-mini parsing с fallback на локальный NLP парсер
        data = parse_voice_text_with_openai(transcription, api_key=key)
        if not data or not data.get("items"):
            data = parse_text_locally(transcription)
            
        if data:
            data["transcription"] = transcription
            return data
        return {"error": f"Распознан текст: «{transcription}», но позиции товаров не определены. Укажите название и цену.", "transcription": transcription}
    except Exception as e:
        print(f"OpenAI Audio error: {e}")
        return {"error": f"Ошибка обработки аудио: {e}"}

def parse_voice_text_with_openai(text_input: str, api_key: str = "") -> Optional[Dict[str, Any]]:
    """Парсинг текста приемки через OpenAI GPT-4o-mini"""
    key = get_active_openai_key(api_key)
    if not key:
        return None
    try:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": VOICE_PARSE_PROMPT},
                {"role": "user", "content": f"Текст сообщения приемщика:\n{text_input}"}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        if resp.status_code == 200:
            content = resp.json()["choices"][0]["message"]["content"]
            data = json.loads(clean_json_response(content))
            data["source_type"] = "voice_openai"
            return data
        else:
            return None
    except Exception as e:
        print(f"OpenAI Voice text error: {e}")
        return None

# =========================================================================
# GEMINI REAL IMPLEMENTATION (Flash Vision & Audio)
# =========================================================================
def parse_invoice_with_gemini(image_bytes: bytes, api_key: str = "") -> Optional[Dict[str, Any]]:
    """Парсинг фото накладной через прямой REST API Gemini Flash"""
    key = get_active_gemini_key(api_key)
    if not key:
        return None
        
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
        b64_img = base64.b64encode(image_bytes).decode("utf-8")
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": INVOICE_PARSE_PROMPT},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": b64_img
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1
            }
        }
        
        resp = requests.post(url, json=payload, timeout=20)
        if resp.status_code == 200:
            result_json = resp.json()
            text = result_json["candidates"][0]["content"]["parts"][0]["text"]
            cleaned = clean_json_response(text)
            data = json.loads(cleaned)
            data["source_type"] = "photo_ai"
            return data
        else:
            print(f"Gemini API HTTP Error {resp.status_code}: {resp.text}")
            return None
    except Exception as e:
        print(f"Gemini Vision error: {e}")
        return None

def parse_voice_audio_bytes_with_gemini(audio_bytes: bytes, mime_type: str = "audio/ogg", api_key: str = "") -> Optional[Dict[str, Any]]:
    """Мультимодальный анализ голосовых аудиосообщений через Gemini Flash Audio"""
    key = get_active_gemini_key(api_key)
    if not key:
        return None

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
        b64_audio = base64.b64encode(audio_bytes).decode("utf-8")

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": VOICE_PARSE_PROMPT},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": b64_audio
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1
            }
        }

        resp = requests.post(url, json=payload, timeout=25)
        if resp.status_code == 200:
            result_json = resp.json()
            text = result_json["candidates"][0]["content"]["parts"][0]["text"]
            cleaned = clean_json_response(text)
            data = json.loads(cleaned)
            data["source_type"] = "voice_audio_ai"
            return data
        else:
            print(f"Gemini Audio API HTTP Error {resp.status_code}: {resp.text}")
            return None
    except Exception as e:
        print(f"Gemini Audio error: {e}")
        return None

def parse_voice_text_with_gemini(text_input: str, api_key: str = "") -> Optional[Dict[str, Any]]:
    """Парсинг текста голосовой приемки через Gemini Flash"""
    key = get_active_gemini_key(api_key)
    if not key:
        return None
        
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{VOICE_PARSE_PROMPT}\n\nТекст сообщения приемщика:\n{text_input}"}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1
            }
        }
        
        resp = requests.post(url, json=payload, timeout=12)
        if resp.status_code == 200:
            result_json = resp.json()
            text = result_json["candidates"][0]["content"]["parts"][0]["text"]
            cleaned = clean_json_response(text)
            data = json.loads(cleaned)
            data["source_type"] = "voice_text_ai"
            return data
        else:
            return None
    except Exception as e:
        print(f"Gemini Voice text error: {e}")
        return None

# =========================================================================
# ДЕМО-ОБРАЗЦЫ ДЛЯ ВЫСТУПЛЕНИЯ
# =========================================================================
def get_demo_sample_invoice(sample_id: str = "spike_milk_flour") -> Dict[str, Any]:
    if sample_id == "spike_milk_flour":
        return {
            "invoice_number": "KZ-7841/Т",
            "supplier_name": "ТОО 'Прима Дистрибьюшн Тараз'",
            "date": "2026-10-14",
            "source_type": "demo_sample",
            "items": [
                {
                    "product_name": "Молоко 'Родина' 3.2% 1л",
                    "category": "Молочная продукция",
                    "quantity": 25.0,
                    "unit": "шт",
                    "purchase_price": 440.0,
                    "total_price": 11000.0
                },
                {
                    "product_name": "Мука пшеничная 'Цесна' 1-сорт 2кг",
                    "category": "Бакалея",
                    "quantity": 10.0,
                    "unit": "шт",
                    "purchase_price": 760.0,
                    "total_price": 7600.0
                },
                {
                    "product_name": "Чай черный 'Пиала Gold' 250г",
                    "category": "Чай/Кофе",
                    "quantity": 15.0,
                    "unit": "шт",
                    "purchase_price": 950.0,
                    "total_price": 14250.0
                },
                {
                    "product_name": "Макароны 'Султан' Спагетти 400г",
                    "category": "Бакалея",
                    "quantity": 30.0,
                    "unit": "шт",
                    "purchase_price": 320.0,
                    "total_price": 9600.0
                }
            ]
        }
    elif sample_id == "kazakh_voice":
        return {
            "invoice_number": "Голос-Тараз-09",
            "supplier_name": "ИП 'Ахметов' (Оптовый склад Аулие-Ата)",
            "date": "2026-10-14",
            "source_type": "voice_kaz",
            "items": [
                {
                    "product_name": "Масло растительное 'Шедевр' 1л",
                    "category": "Бакалея",
                    "quantity": 20.0,
                    "unit": "шт",
                    "purchase_price": 840.0,
                    "total_price": 16800.0
                },
                {
                    "product_name": "Сахар песок 1кг",
                    "category": "Бакалея",
                    "quantity": 50.0,
                    "unit": "кг",
                    "purchase_price": 410.0,
                    "total_price": 20500.0
                },
                {
                    "product_name": "Рис 'Акмаржан' 1кг",
                    "category": "Бакалея",
                    "quantity": 15.0,
                    "unit": "кг",
                    "purchase_price": 520.0,
                    "total_price": 7800.0
                }
            ]
        }
    else:
        return {
            "invoice_number": "RG-2026-004",
            "supplier_name": "ТОО 'RG Brands Тараз'",
            "date": "2026-10-14",
            "source_type": "demo_sample",
            "items": [
                {
                    "product_name": "Вода 'Tassay' 1.5л",
                    "category": "Напитки",
                    "quantity": 60.0,
                    "unit": "шт",
                    "purchase_price": 170.0,
                    "total_price": 10200.0
                },
                {
                    "product_name": "Чай черный 'Пиала Gold' 250г",
                    "category": "Чай/Кофе",
                    "quantity": 20.0,
                    "unit": "шт",
                    "purchase_price": 950.0,
                    "total_price": 19000.0
                }
            ]
        }

# =========================================================================
# ЛОКАЛЬНЫЙ NLP / REGEX ПАРСЕР ТЕКСТА (КАЗАХСКИЙ И РУССКИЙ ЯЗЫКИ)
# =========================================================================
def parse_text_locally(text: str) -> Optional[Dict[str, Any]]:
    """
    Извлечение номенклатуры из текста без обращения к внешним LLM.
    Поддерживает казахские и русские шаблоны закупа:
    - 'Молоко Родина 25 шт по 440 тг'
    - '20 сүт 440 теңгеден'
    - '15 қап ұн 8500-ден'
    - 'Мука Цесна 10 кг 760'
    """
    if not text or not text.strip():
        return None
        
    lines = [l.strip() for l in re.split(r'[\n;,]+', text) if l.strip()]
    items = []
    
    unit_re = r'(?:шт|кг|л|литр|пачка|пач|кор|коробка|қап|бөтелке|бут|дана|порция|банка)'
    
    for line in lines:
        cleaned = re.sub(r'^(купил|привезли|принял|поступило|келді|алдық|закуп|товар|по)\s*', '', line, flags=re.IGNORECASE).strip()
        if not cleaned or len(cleaned) < 2:
            continue
            
        matched = False
        
        # Если строка начинается с цифры: '20 сүт 440 теңгеден' или '15 қап ұн 8500'
        if re.match(r'^\d', cleaned):
            m2 = re.search(r'^(\d+(?:[.,]\d+)?)\s*(?:(' + unit_re + r')\s+)?(.*?)\s+(?:по|-нен|-тен|-дан|-ден)?\s*(\d+(?:[.,]\d+)?)\s*(?:тг|тенге|теңге|теңгеден|ден|нен|тен|₸|kzt)?$', cleaned, re.IGNORECASE)
            if m2:
                q = float(m2.group(1).replace(',', '.'))
                u = m2.group(2) or 'шт'
                n = m2.group(3).strip()
                p = float(m2.group(4).replace(',', '.'))
                if n:
                    items.append({
                        "product_name": n,
                        "category": "Продукты",
                        "quantity": q,
                        "unit": u,
                        "purchase_price": p,
                        "total_price": q * p
                    })
                    matched = True
                    
        # Иначе: 'Молоко Родина 25 шт по 440 тг' или 'Мука 10 кг 760'
        if not matched:
            m1 = re.search(r'^(.*?)\s+[-:]?\s*(\d+(?:[.,]\d+)?)\s*(?:(' + unit_re + r')\s*)?(?:по|-нен|-тен|-дан|-ден)?\s*(\d+(?:[.,]\d+)?)\s*(?:тг|тенге|теңге|теңгеден|ден|нен|тен|₸|kzt)?$', cleaned, re.IGNORECASE)
            if m1 and not m1.group(1).strip().isdigit():
                n = m1.group(1).strip()
                q = float(m1.group(2).replace(',', '.'))
                u = m1.group(3) or 'шт'
                p = float(m1.group(4).replace(',', '.'))
                if n:
                    items.append({
                        "product_name": n,
                        "category": "Продукты",
                        "quantity": q,
                        "unit": u,
                        "purchase_price": p,
                        "total_price": q * p
                    })
                    matched = True
                    
        # Fallback на случай свободной фразы: найти числа и слова
        if not matched:
            nums = re.findall(r'\b\d+(?:[.,]\d+)?\b', cleaned)
            if len(nums) >= 2:
                q = float(nums[0].replace(',', '.'))
                p = float(nums[1].replace(',', '.'))
                n = re.sub(r'\b\d+(?:[.,]\d+)?\b', '', cleaned)
                n = re.sub(r'\b(шт|кг|л|литр|по|тг|тенге|теңге|теңгеден|ден|нен|тен|₸|дана|қап)\b', '', n, flags=re.IGNORECASE).strip()
                if n:
                    items.append({
                        "product_name": n,
                        "category": "Продукты",
                        "quantity": q,
                        "unit": "шт",
                        "purchase_price": p,
                        "total_price": q * p
                    })
                    
    if items:
        return {
            "invoice_number": "Закуп-Текст",
            "supplier_name": "Поставщик (ручной ввод)",
            "date": "Сегодня",
            "source_type": "local_nlp_text",
            "items": items
        }
    return None

# =========================================================================
# ЕДИНАЯ ТОЧКА ВХОДА (РЕАЛЬНАЯ ОБРАБОТКА БЕЗ СУРРОГАТОВ И ФЕЙКОВЫХ ЗАГЛУШЕК)
# =========================================================================
def process_invoice(
    image_bytes: Optional[bytes] = None,
    audio_bytes: Optional[bytes] = None,
    audio_mime: str = "audio/ogg",
    voice_text: Optional[str] = None,
    sample_id: Optional[str] = None,
    api_key: str = ""
) -> Dict[str, Any]:
    raw_data = None
    openai_key = get_active_openai_key(api_key if api_key.startswith("sk-") else "")
    gemini_key = get_active_gemini_key(api_key if not api_key.startswith("sk-") else "")
    
    if image_bytes:
        # 1. Попытка через OpenAI GPT-4o-mini Vision
        if openai_key:
            raw_data = parse_invoice_with_openai(image_bytes, openai_key)
        # 2. Попытка через Gemini Vision
        if not raw_data and gemini_key:
            raw_data = parse_invoice_with_gemini(image_bytes, gemini_key)
        # При сбое НЕ подменяем на фейковые товары — честно сообщаем об ошибке
        if not raw_data or not raw_data.get("items"):
            return {
                "status": "error",
                "error": "Не удалось распознать фото накладной. Убедитесь, что текст четкий и хорошо освещен, либо отправьте позиции текстом.",
                "items": [],
                "source_type": "photo_error"
            }
            
    elif audio_bytes:
        # 1. Попытка через OpenAI Whisper + GPT-4o-mini
        if openai_key:
            raw_data = parse_voice_audio_bytes_with_openai(audio_bytes, audio_mime, openai_key)
        # 2. Попытка через Gemini Audio
        if not raw_data and gemini_key:
            raw_data = parse_voice_audio_bytes_with_gemini(audio_bytes, audio_mime, gemini_key)
            
        if isinstance(raw_data, dict) and raw_data.get("error"):
            return {
                "status": "error",
                "error": raw_data["error"],
                "items": [],
                "source_type": "audio_error",
                "transcription": raw_data.get("transcription", "")
            }
            
        # При сбое НЕ подменяем на фейк
        if not raw_data or not raw_data.get("items"):
            key_hint = "" if (openai_key or gemini_key) else " (Внимание: OpenAI / Gemini API ключ не настроен в сервисах)"
            return {
                "status": "error",
                "error": f"Не удалось распознать позиции в аудиосообщении{key_hint}. Пожалуйста, повторите четче или отправьте текстом (например: «Молоко 20 шт по 440 тг»).",
                "items": [],
                "source_type": "audio_error"
            }
            
    elif voice_text:
        # 1. Попытка через OpenAI GPT-4o-mini
        if openai_key:
            raw_data = parse_voice_text_with_openai(voice_text, openai_key)
        # 2. Попытка через Gemini
        if not raw_data and gemini_key:
            raw_data = parse_voice_text_with_gemini(voice_text, gemini_key)
        # 3. Локальный NLP парсер текста (Казахский и Русский)
        if not raw_data or not raw_data.get("items"):
            raw_data = parse_text_locally(voice_text)
            
        if not raw_data or not raw_data.get("items"):
            return {
                "status": "error",
                "error": "Не удалось выделить товары из текста. Укажите название, количество и цену (например: «Кола 10 шт по 450 тг» или «20 сүт 440 теңгеден»).",
                "items": [],
                "source_type": "text_error"
            }
            
    elif sample_id:
        raw_data = get_demo_sample_invoice(sample_id)
    else:
        return {
            "status": "error",
            "error": "Нет данных для обработки. Отправьте фото, голос или текст.",
            "items": []
        }
        
    analyzed = analyze_invoice_pricing(raw_data)
    return analyzed
