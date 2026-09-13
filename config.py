# -*- coding: utf-8 -*-
"""
تنظیمات اصلی ربات.
همه مقادیر حساس را در فایل .env یا متغیرهای محیطی ست کنید.

مثال .env:
    BOT_TOKEN=1234567890:AABBccDDeeFF...
    ADMIN_IDS=123456789,987654321
    BOT_NAME=همخوانی
    BOT_DESCRIPTION=ربات مدیریت همخوانی کتاب
    BOT_SHORT_DESCRIPTION=ربات همخوانی
"""
import os
from dotenv import load_dotenv

load_dotenv()

# توکن ربات که از @BotFather گرفته‌اید - اجباری
BOT_TOKEN = os.environ["BOT_TOKEN"]

# آیدی عددی تلگرام ادمین‌ها - چند آیدی با ویرگول جدا کنید
# مثال: ADMIN_IDS=123456789,987654321
_raw_admin_ids = os.getenv("ADMIN_IDS", "")
ADMIN_IDS: set[int] = {
    int(x.strip())
    for x in _raw_admin_ids.split(",")
    if x.strip().isdigit()
}
if not ADMIN_IDS:
    raise ValueError(
        "متغیر محیطی ADMIN_IDS تنظیم نشده یا خالی است.\n"
        "مثال: ADMIN_IDS=123456789,987654321"
    )

# مسیر فایل دیتابیس sqlite
DB_PATH = os.getenv("DB_PATH", "readalong.db")

# ساعت پیش‌فرض ارسال یادآوری روزانه (ساعت تهران، 24 ساعته) به فرمت HH:MM
DAILY_REMINDER_TIME = os.getenv("DAILY_REMINDER_TIME", "09:00")

# نام تایم‌زون (برای jobqueue و تاریخ‌ها)
TIMEZONE = os.getenv("TIMEZONE", "Asia/Tehran")

# نام ربات که در BotFather ست می‌شود (اختیاری - اگر خالی باشد ست نمی‌شود)
BOT_NAME = os.getenv("BOT_NAME", "")

# توضیح کامل ربات (اختیاری)
BOT_DESCRIPTION = os.getenv("BOT_DESCRIPTION", "")

# توضیح کوتاه ربات (اختیاری)
BOT_SHORT_DESCRIPTION = os.getenv("BOT_SHORT_DESCRIPTION", "")