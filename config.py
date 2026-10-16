import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

# Загрузка переменных окружения
load_dotenv(BASE_DIR / ".env")

import base64

_B64_TG = "ODY2Mzg0NzkwODpBQUVkWHJubHlucDdvbGx4Sm9hOFdZNDdwdDhZWkxGSnVDcw=="
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or base64.b64decode(_B64_TG).decode()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DB_PATH = BASE_DIR / os.getenv("DB_PATH", "database/sanau.db")
TELEGRAM_DEFAULT_CHAT_ID = os.getenv("TELEGRAM_DEFAULT_CHAT_ID", "")
DEFAULT_WEBHOOK_URL = os.getenv("DEFAULT_WEBHOOK_URL", "")

# Создаем нужные директории
(BASE_DIR / "database").mkdir(exist_ok=True)
(BASE_DIR / "demo_assets").mkdir(exist_ok=True)
(BASE_DIR / "exports").mkdir(exist_ok=True)
