# -*- coding: utf-8 -*-
"""
جاب‌های زمان‌بندی‌شده:
1) یادآوری روزانه به کاربران در پیوی (ساعت DAILY_REMINDER_TIME)
2) جاب شبانه (ساعت 00:00):
   - در تاپیک «پیگیری» هر کتاب فعال، برنامه‌ی کامل روزها را با تیک ✅ برای
     روزهای گذشته پست می‌کند.
   - سپس گزارش روز قبل (تعداد اعضا، خوانده‌ها، نخوانده‌ها) را می‌فرستد.
"""
import datetime
import logging

from telegram.ext import ContextTypes

import database as db
from utils.keyboards import yes_no_kb
from utils.jalali import parse_jalali, format_jalali_human, days_with_human
from utils.formatting import format_nightly_schedule, format_previous_day_report

logger = logging.getLogger(__name__)


# ------------------------------------------------------------- reminders --

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
            progress = db.get_progress_for_user(rday["id"], u["id"])
            if progress and progress["status"] != "pending":
                continue
            try:
                await context.bot.send_message(
                    chat_id=u["telegram_id"],
                    text=text,
                    reply_markup=yes_no_kb("track", rday["id"]),
                )
            except Exception as e:
                logger.warning("نتونستم به %s پیام بدم: %s", u["telegram_id"], e)

        db.mark_reminder_sent(rday["id"])


# --------------------------------------------------- nightly job (00:00) --

async def send_nightly_schedule_and_report(context: ContextTypes.DEFAULT_TYPE):
    today_g = str(datetime.date.today())
    yesterday_g = str(datetime.date.today() - datetime.timedelta(days=1))

    books = db.list_books(status="active")
    for book in books:
        if not book["group_chat_id"]:
            continue

        days = db.get_reading_days(book["id"])
        if not days:
            continue

        # 1) ارسال برنامه کامل با تیک ✅ برای روزهای قبل
        try:
            await context.bot.send_message(
                chat_id=book["group_chat_id"],
                message_thread_id=book["topic_pigiri_id"],
                text=format_nightly_schedule(book, days_with_human(days)),
            )
        except Exception as e:
            logger.warning(
                "خطا در ارسال برنامه‌ی شبانه برای کتاب %s: %s", book["id"], e
            )
            continue

        # 2) ارسال گزارش روز قبل (اگر روزی برای دیروز ثبت شده بود)
        yesterday_days = [d for d in days if d["gregorian_date"] == yesterday_g]
        if not yesterday_days:
            continue

        rday = yesterday_days[0]
        rows = db.get_progress_for_day(rday["id"])
        jd = parse_jalali(rday["jalali_date"])
        human = format_jalali_human(jd)

        try:
            await context.bot.send_message(
                chat_id=book["group_chat_id"],
                message_thread_id=book["topic_pigiri_id"],
                text=format_previous_day_report(human, rows),
            )
        except Exception as e:
            logger.warning(
                "خطا در ارسال گزارش روز قبل برای کتاب %s: %s", book["id"], e
            )


# ----------------------------------------------------------------- jobs --

def setup_jobs(application):
    """این تابع را در بوت اصلی صدا بزن تا جاب‌ها رجیستر بشن."""
    from config import DAILY_REMINDER_TIME, TIMEZONE
    import datetime as dt

    try:
        from zoneinfo import ZoneInfo

        tzinfo = ZoneInfo(TIMEZONE)
    except Exception:
        tzinfo = None

    # جاب یادآوری روزانه به کاربران
    hour, minute = (int(x) for x in DAILY_REMINDER_TIME.split(":"))
    run_time = dt.time(hour=hour, minute=minute, tzinfo=tzinfo)
    application.job_queue.run_daily(
        send_daily_reminders,
        time=run_time,
        name="daily_reading_reminder",
    )

    # جاب شبانه: ساعت 00:00 برنامه + گزارش روز قبل را در تاپیک‌ها می‌فرستد
    midnight = dt.time(hour=0, minute=0, tzinfo=tzinfo)
    application.job_queue.run_daily(
        send_nightly_schedule_and_report,
        time=midnight,
        name="nightly_schedule_and_report",
    )