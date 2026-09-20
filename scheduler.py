# -*- coding: utf-8 -*-
"""
جاب‌های زمان‌بندی‌شده:

1) یادآوری روزانه به کاربران در پیوی (ساعت DAILY_REMINDER_TIME)
2) جاب ساعت 21:00 تهران:
   - برنامه کامل روزها با تیک ✅ برای روزهای گذشته (و روز جاری تیک‌دار)
   - گزارش همون روز (تا اون لحظه چه کسانی خوندن، چه کسانی نخوندن)
   - زیر پیام: «آفرین :) می‌ریم واسه روز بعدی»
"""
import datetime
import logging

from telegram.ext import ContextTypes

import database as db
from utils.keyboards import yes_no_kb
from utils.jalali import parse_jalali, format_jalali_human, days_with_human, today_jalali, format_jalali_full
from utils.formatting import format_nightly_schedule, format_previous_day_report

logger = logging.getLogger(__name__)


# ------------------------------------------------------------- reminders --

async def send_daily_reminders(context: ContextTypes.DEFAULT_TYPE):
    try:
        today_g = str(datetime.date.today())
        reading_days = db.get_reading_days_by_gregorian_date(today_g)

        for rday in reading_days:
            try:
                book = db.get_book(rday["book_id"])
                if not book or book["status"] != "active":
                    continue

                db.ensure_progress_rows(rday["id"], book["id"])
                users = db.get_registered_users(book["id"])
                jd = parse_jalali(rday["jalali_date"])
                human_date = format_jalali_human(jd)

                # خط پی‌دی‌اف فقط اگه وجود داشت
                pdf_line = ""
                if rday["pdf_page_from"] and rday["pdf_page_to"]:
                    pdf_line = f"\n💻 پی‌دی‌اف {rday['pdf_page_from']} تا {rday['pdf_page_to']}"

                text = (
                    f"📖 «{book['title']}»\n"
                    f"🗓 امروز: {human_date}\n"
                    f"📚 صفحه {rday['book_page_from']} تا {rday['book_page_to']}"
                    f"{pdf_line}\n\n"
                    "بخش امروز رو خوندی؟"
                )

                for u in users:
                    try:
                        progress = db.get_progress_for_user(rday["id"], u["id"])
                        if progress and progress["status"] != "pending":
                            continue
                        await context.bot.send_message(
                            chat_id=u["telegram_id"],
                            text=text,
                            reply_markup=yes_no_kb("track", rday["id"]),
                        )
                    except Exception as e:
                        logger.warning("نتونستم به %s پیام بدم: %s", u["telegram_id"], e)

                db.mark_reminder_sent(rday["id"])

            except Exception as e:
                logger.error("خطا در پردازش reading_day %s: %s", rday.get("id"), e)

    except Exception as e:
        logger.error("خطا کلی در send_daily_reminders: %s", e)


# --------------------------------------------------- evening job (21:00) --

def _format_evening_schedule(book, days: list) -> str:
    """
    برنامه شبانه ساعت 21:
    - روزهای قبل از امروز: ✅
    - روز امروز: ✅ (تیک‌دار چون گزارش اعلام شده)
    - روزهای آینده: بدون تیک
    """
    today_g = str(datetime.date.today())
    lines = [f"📖 «{book['title']}»", ""]
    for d in days:
        is_today = d["gregorian_date"] == today_g
        is_past = d["gregorian_date"] < today_g
        date_line = f"🗓 {d['jalali_date_human']}"
        if is_past or is_today:
            date_line += " ✅"
        lines.append(date_line)
        lines.append(f"📚 کتاب: صفحه {d['book_page_from']} تا {d['book_page_to']}")
        if d.get("pdf_page_from") and d.get("pdf_page_to"):
            lines.append(f"💻 پی دی اف : {d['pdf_page_from']} تا {d['pdf_page_to']}")
        lines.append("")
    return "\n".join(lines).strip()


def _format_today_report(jalali_date_human: str, rows) -> str:
    """
    گزارش همون روز تا ساعت 21:
    - چه کسانی خوندن
    - چه کسانی نخوندن
    """
    read_users, not_read_users = [], []
    for r in rows:
        name = (
            r["full_name"]
            or (f"@{r['username']}" if r["username"] else str(r["telegram_id"]))
        )
        if r["status"] == "read":
            read_users.append(name)
        else:
            not_read_users.append(name)

    lines = [f"📊 گزارش امروز — {jalali_date_human}", ""]
    lines.append(f"✅ خوانده‌اند ({len(read_users)}):")
    for n in read_users:
        lines.append(f"   - {n}")
    if not read_users:
        lines.append("   (هیچ‌کس)")
    lines.append("")
    lines.append(f"❌ نخوانده‌اند ({len(not_read_users)}):")
    for n in not_read_users:
        lines.append(f"   - {n}")
    if not not_read_users:
        lines.append("   (هیچ‌کس)")
    return "\n".join(lines)


async def send_evening_schedule_and_report(context: ContextTypes.DEFAULT_TYPE):
    """ساعت 21 برنامه کامل + گزارش همون روز + پیام آفرین ارسال می‌شود."""
    try:
        today_g = str(datetime.date.today())
        books = db.list_books(status="active")

        for book in books:
            try:
                if not book["group_chat_id"]:
                    continue

                days = db.get_reading_days(book["id"])
                if not days:
                    continue

                days_human = days_with_human(days)

                # 1) برنامه کامل با تیک روز جاری
                try:
                    schedule_text = _format_evening_schedule(book, days_human)
                    await context.bot.send_message(
                        chat_id=book["group_chat_id"],
                        message_thread_id=book["topic_pigiri_id"],
                        text=schedule_text,
                    )
                except Exception as e:
                    logger.warning("خطا در ارسال برنامه شبانه برای کتاب %s: %s", book["id"], e)
                    continue

                # 2) گزارش همون روز
                today_days = [d for d in days if d["gregorian_date"] == today_g]
                if today_days:
                    rday = today_days[0]
                    db.ensure_progress_rows(rday["id"], book["id"])
                    rows = db.get_progress_for_day(rday["id"])
                    jd = parse_jalali(rday["jalali_date"])
                    human = format_jalali_human(jd)

                    try:
                        report_text = _format_today_report(human, rows)
                        # پیام آفرین زیر گزارش
                        report_text += "\n\n🌟 آفرین :) می‌ریم واسه روز بعدی"
                        await context.bot.send_message(
                            chat_id=book["group_chat_id"],
                            message_thread_id=book["topic_pigiri_id"],
                            text=report_text,
                        )
                    except Exception as e:
                        logger.warning("خطا در ارسال گزارش شبانه برای کتاب %s: %s", book["id"], e)

            except Exception as e:
                logger.error("خطا در پردازش کتاب %s در جاب شبانه: %s", book.get("id"), e)

    except Exception as e:
        logger.error("خطا کلی در send_evening_schedule_and_report: %s", e)


# ----------------------------------------------------------------- jobs --

def setup_jobs(application):
    """این تابع را در بوت اصلی صدا بزن تا جاب‌ها رجیستر بشن."""
    from config import DAILY_REMINDER_TIME, TIMEZONE
    import datetime as dt

    try:
        from zoneinfo import ZoneInfo
        tzinfo = ZoneInfo(TIMEZONE)
    except Exception:
        try:
            import pytz
            tzinfo = pytz.timezone(TIMEZONE)
        except Exception:
            tzinfo = None
            logger.warning("تایم‌زون %s پیدا نشد، از UTC استفاده می‌شه", TIMEZONE)

    # جاب یادآوری روزانه به کاربران
    hour, minute = (int(x) for x in DAILY_REMINDER_TIME.split(":"))
    run_time = dt.time(hour=hour, minute=minute, tzinfo=tzinfo)
    application.job_queue.run_daily(
        send_daily_reminders,
        time=run_time,
        name="daily_reading_reminder",
    )
    logger.info("جاب یادآوری روزانه ساعت %s:%s ثبت شد", hour, minute)

    # جاب شبانه ساعت 21:00: برنامه + گزارش همون روز
    evening_time = dt.time(hour=21, minute=0, tzinfo=tzinfo)
    application.job_queue.run_daily(
        send_evening_schedule_and_report,
        time=evening_time,
        name="evening_schedule_and_report",
    )
    logger.info("جاب شبانه ساعت 21:00 ثبت شد")