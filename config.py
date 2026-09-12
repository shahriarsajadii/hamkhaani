# -*- coding: utf-8 -*-
"""
تنظیمات اصلی ربات.
مقادیر حساس را از طریق متغیرهای محیطی (Environment Variables) ست کنید،
یا مستقیم همینجا جایگزین کنید (فقط برای تست/توسعه توصیه می‌شود).
"""
import os

# توکن ربات که از @BotFather گرفته‌اید
BOT_TOKEN = os.getenv("BOT_TOKEN", "8627635911:AAFITol3cnBfBPzu6QnXC-bto79Uw4loi2M")

# آیدی عددی تلگرام ادمین‌ها (می‌توانید چند نفر بگذارید)
# می‌توانید آیدی عددی خودتان را از ربات‌هایی مثل @userinfobot بگیرید
# ADMIN_IDS = {
#     int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()
# }
ADMIN_IDS = {802676229}

# اگر می‌خواهید مستقیم در کد بنویسید (بدون env)، خط پایین را باز کنید:
# ADMIN_IDS = {123456789, 987654321}

# مسیر فایل دیتابیس sqlite
DB_PATH = os.getenv("DB_PATH", "readalong.db")

# ساعت پیش‌فرض ارسال یادآوری روزانه (ساعت تهران، 24 ساعته) به فرمت HH:MM
DAILY_REMINDER_TIME = os.getenv("DAILY_REMINDER_TIME", "09:00")

# نام تایم‌زون (برای jobqueue و تاریخ‌ها)
TIMEZONE = os.getenv("TIMEZONE", "Asia/Tehran")
