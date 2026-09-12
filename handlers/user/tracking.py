# -*- coding: utf-8 -*-
"""
پیگیری روزانه:
  - کاربر با دکمه «✅ گزارش امروز» می‌تونه دستی اعلام کنه که بخش امروز رو خونده یا نه.
  - همچنین اسکجولر هر روز به‌صورت خودکار (job) برای کاربرهای ثبت‌نامی، همین دکمه‌ها رو
    توی پیام خصوصی می‌فرسته (نگاه کن به scheduler.py).
  - در هر دو حالت، پاسخ نهایی هم در دیتابیس ذخیره و هم در تاپیک «پیگیری» گروه اعلام می‌شود.
"""
import datetime
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, CallbackQueryHandler, filters

import database as db
from utils.keyboards import yes_no_kb, USER_MENU
from utils.jalali import parse_jalali, format_jalali_human, today_jalali
from utils.formatting import format_daily_report_line


async def today_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """کاربر دستی می‌خواد وضعیت امروزش رو گزارش بده."""
    tg_user = update.effective_user
    user_row = db.get_user_by_telegram_id(tg_user.id)
    if not user_row:
        await update.message.reply_text("اول باید توی یه کتاب ثبت‌نام کنی.")
        return

    today_g = str(datetime.date.today())
    active_books = db.get_user_books(user_row["id"], status="active")
    if not active_books:
        await update.message.reply_text("توی هیچ کتاب فعالی ثبت‌نام نکردی.")
        return

    found_any = False
    for book in active_books:
        days = db.get_reading_days(book["id"])
        today_days = [d for d in days if d["gregorian_date"] == today_g]
        for rday in today_days:
            found_any = True
            jd = parse_jalali(rday["jalali_date"])
            await update.message.reply_text(
                f"📖 «{book['title']}»\n🗓 {format_jalali_human(jd)}\n"
                f"📚 صفحه {rday['book_page_from']} تا {rday['book_page_to']}\n\n"
                "بخش امروز رو خوندی؟",
                reply_markup=yes_no_kb("track", rday["id"]),
            )
    if not found_any:
        await update.message.reply_text("برای امروز، بخشی توی برنامه کتاب‌های تو ثبت نشده.")


today_report_handler = MessageHandler(filters.Regex("^✅ گزارش امروز$"), today_report)


async def tracking_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پاسخ به دکمه‌های بله/خیر (چه دستی، چه از یادآوری خودکار)."""
    query = update.callback_query
    await query.answer()
    _, answer, reading_day_id = query.data.split(":")
    reading_day_id = int(reading_day_id)

    tg_user = update.effective_user
    user_row = db.get_user_by_telegram_id(tg_user.id)
    if not user_row:
        await query.edit_message_text("خطا: کاربر پیدا نشد.")
        return

    rday = db.get_reading_day(reading_day_id)
    status = "read" if answer == "yes" else "not_read"
    db.set_progress(reading_day_id, user_row["id"], status)

    jd = parse_jalali(rday["jalali_date"])
    human_date = format_jalali_human(jd)

    await query.edit_message_text(
        "✅ ثبت شد. ممنون که خبر دادی!" if answer == "yes" else "دریافت شد. هر وقت خوندی خبر بده 🙌"
    )

    # اعلام در تاپیک «پیگیری» گروه
    book = db.get_book(rday["book_id"])
    if book["group_chat_id"] and book["topic_pigiri_id"]:
        full_name = user_row["full_name"] or (f"@{user_row['username']}" if user_row["username"] else "کاربر")
        line = format_daily_report_line(full_name, human_date, answer == "yes")
        try:
            await context.bot.send_message(
                chat_id=book["group_chat_id"],
                message_thread_id=book["topic_pigiri_id"],
                text=line,
            )
        except Exception:
            # اگه دسترسی یا تاپیک مشکل داشت، جلوی کرش کردن ربات رو می‌گیریم
            pass


tracking_callback_handler = CallbackQueryHandler(tracking_callback, pattern="^track:")
