import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
    DATABASE = os.path.join(BASE_DIR, "instance", "timecash.db")
    UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
    PAYMENT_NUMBER = os.getenv("TIME_CASH_PAYMENT_NUMBER", "256707281801")
    OWNER_EMAIL = os.getenv("OWNER_EMAIL", "")
    ADMIN_PASSCODE = os.getenv("ADMIN_PASSCODE", "")
    SMTP_HOST = os.getenv("SMTP_HOST", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
