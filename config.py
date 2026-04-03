import os
from dotenv import load_dotenv

# تحميل المتغيرات من .env (للاستخدام المحلي)
load_dotenv()

# ---------- Telegram ----------
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ---------- AI ----------
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# ---------- Database ----------
DATABASE_URL = os.getenv("DATABASE_URL")

# ---------- System ----------
OWNER_ID = int(os.getenv("OWNER_ID", "0"))  # ضع آيديك هنا

# ---------- Bot Control ----------
BOT_ACTIVE = True  # يمكن إيقافه من الأدمن لاحقاً
