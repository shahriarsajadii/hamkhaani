# -*- coding: utf-8 -*-
"""
جاب روزانه که با JobQueue کتابخانه python-telegram-bot اجرا می‌شود.
هر روز، در ساعت تنظیم‌شده (config.DAILY_REMINDER_TIME):
  - روزهایی که gregorian_date == امروز باشه رو پیدا می‌کنه
  - برای هر کاربر ثبت‌نام‌کرده، یه ردیف pending در daily_progress می‌سازه (اگه نبود)
  - برای هر کاربر پیام خصوصی با دکمه‌ی بله/خیر می‌فرسته
"""
import datetime
import logging
from telegram.ext import ContextTypes

import database as db
from utils.keyboards import yes_no_kb
from utils.jalali import parse_jalali, format_jalali_human

logger = logging.getLogger(__name__)


async def send_daily_reminders(context: ContextTypes.DEFAULT_TYPE):
    today_g = str(datetime.date.today())
    reading_days = db.get_reading_days_by_gregorian_date(today_g)

    for rday in reading_days:
        book = db.get_book(rday["book_id"])
        if book["status"] != "active":
            continue

        db.ensure_progress_rows(rday["id"], book["id"])
        users = db.get_registered_users(book["id"])
        jd = parse_jalali(rday["jalali_date"])
        human_date = format_jalali_human(jd)

        text = (
            f"📖 «{book['title']}»\n"
            f"🗓 امروز: {human_date}\n"
            f"📚 صفحه {rday['book_page_from']} تا {rday['book_page_to']}\n"
            f"💻 پی‌دی‌اف {rday['pdf_page_from']} تا {rday['pdf_page_to']}\n\n"
            "بخش امروز رو خوندی؟"
        )

        for u in users:
            try:
                await context.bot.send_message(
                    chat_id=u["telegram_id"],
                    text=text,
                    reply_markup=yes_no_kb("track", rday["id"]),
                )
            except Exception as e:
                logger.warning("نتونستم به %s پیام بدم: %s", u["telegram_id"], e)

        db.mark_reminder_sent(rday["id"])


def setup_jobs(application):
    """این تابع را در بوت اصلی صدا بزن تا جاب روزانه رجیستر بشه."""
    from config import DAILY_REMINDER_TIME, TIMEZONE
    import datetime as dt
    try:
        from zoneinfo import ZoneInfo
        tzinfo = ZoneInfo(TIMEZONE)
    except Exception:
        tzinfo = None

    hour, minute = (int(x) for x in DAILY_REMINDER_TIME.split(":"))
    run_time = dt.time(hour=hour, minute=minute, tzinfo=tzinfo)
    application.job_queue.run_daily(
        send_daily_reminders,
        time=run_time,
        name="daily_reading_reminder",
    )
