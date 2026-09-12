# -*- coding: utf-8 -*-
"""
تعیین برنامه روزهای همخوانی یک کتاب.
ادمین کتاب رو انتخاب می‌کنه، بعد به ترتیب برای هر روز:
  - تاریخ جلالی (مثال: 1403/06/21)
  - بازه صفحات کتاب (مثال: 1 تا 30)
  - بازه صفحات پی‌دی‌اف (مثال: 3 تا 15)
رو وارد می‌کنه، و در پایان با دکمه «پایان» برنامه رو تأیید و ذخیره می‌کنه.
"""
import re
from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

import database as db
from utils.keyboards import books_kb, ADMIN_MENU, CANCEL_KB
from utils.jalali import parse_jalali, to_gregorian, format_jalali_human
from utils.formatting import format_schedule_announcement
from handlers.common import is_admin
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

CHOOSE_BOOK, ASK_DATE, ASK_BOOK_PAGES, ASK_PDF_PAGES, ASK_CONTINUE = range(5)

CONTINUE_KB = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("➕ افزودن روز بعد", callback_data="sched:more"),
            InlineKeyboardButton("✅ پایان و پیش‌نمایش", callback_data="sched:done"),
        ]
    ]
)


def _extract_two_numbers(text: str):
    nums = re.findall(r"\d+", text)
    if len(nums) < 2:
        raise ValueError("باید دو عدد بفرستی، مثلا: 1 تا 30")
    return int(nums[0]), int(nums[1])


async def schedule_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END
    books = db.list_books(status="draft")
    if not books:
        await update.message.reply_text("هیچ کتاب پیش‌نویسی برای تعیین برنامه وجود نداره.")
        return ConversationHandler.END
    await update.message.reply_text("برای کدوم کتاب برنامه تعیین کنم؟", reply_markup=books_kb(books, "sched_book"))
    return CHOOSE_BOOK


async def schedule_choose_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    book_id = int(query.data.split(":")[1])
    context.user_data["sched_book_id"] = book_id
    context.user_data["sched_days"] = []  # لیست موقت روزها قبل از ثبت نهایی
    await query.edit_message_text("تاریخ روز اول رو به فرمت 1403/06/21 بفرست:")
    return ASK_DATE


async def schedule_ask_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        jdate = parse_jalali(text)
    except ValueError as e:
        await update.message.reply_text(f"تاریخ نامعتبره: {e}\nدوباره امتحان کن (مثال: 1403/06/21)")
        return ASK_DATE
    context.user_data["sched_current_date"] = text
    await update.message.reply_text("بازه صفحات کتاب رو بفرست (مثال: 1 تا 30):")
    return ASK_BOOK_PAGES


async def schedule_ask_book_pages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        f, t = _extract_two_numbers(update.message.text)
    except ValueError as e:
        await update.message.reply_text(str(e))
        return ASK_BOOK_PAGES
    context.user_data["sched_book_from"] = f
    context.user_data["sched_book_to"] = t
    await update.message.reply_text("بازه صفحات پی‌دی‌اف رو بفرست (مثال: 3 تا 15):")
    return ASK_PDF_PAGES


async def schedule_ask_pdf_pages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        f, t = _extract_two_numbers(update.message.text)
    except ValueError as e:
        await update.message.reply_text(str(e))
        return ASK_PDF_PAGES

    day = {
        "jalali_date": context.user_data.pop("sched_current_date"),
        "book_page_from": context.user_data.pop("sched_book_from"),
        "book_page_to": context.user_data.pop("sched_book_to"),
        "pdf_page_from": f,
        "pdf_page_to": t,
    }
    context.user_data["sched_days"].append(day)

    await update.message.reply_text(
        f"روز {len(context.user_data['sched_days'])} ثبت موقت شد ✅\nادامه بدم یا تمومه؟",
        reply_markup=CONTINUE_KB,
    )
    return ASK_CONTINUE


async def schedule_continue_or_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "sched:more":
        await query.edit_message_text("تاریخ روز بعد رو به فرمت 1403/06/21 بفرست:")
        return ASK_DATE

    # sched:done -> پیش‌نمایش و ثبت نهایی
    book_id = context.user_data["sched_book_id"]
    book = db.get_book(book_id)
    days = context.user_data["sched_days"]

    for idx, d in enumerate(days, start=1):
        jdate = parse_jalali(d["jalali_date"])
        db.add_reading_day(
            book_id=book_id,
            day_index=idx,
            jalali_date=d["jalali_date"],
            gregorian_date=to_gregorian(jdate).isoformat(),
            book_from=d["book_page_from"],
            book_to=d["book_page_to"],
            pdf_from=d["pdf_page_from"],
            pdf_to=d["pdf_page_to"],
        )

    saved_days = db.get_reading_days(book_id)
    days_for_format = []
    for d in saved_days:
        jd = parse_jalali(d["jalali_date"])
        days_for_format.append({**dict(d), "jalali_date_human": format_jalali_human(jd)})
    preview = format_schedule_announcement(book, days_for_format)

    await query.edit_message_text(
        "✅ برنامه ذخیره شد. این متنیه که موقع فعال‌سازی کتاب توی تاپیک «گپ» پست می‌شه:\n\n"
        + preview
    )
    context.user_data.pop("sched_days", None)
    context.user_data.pop("sched_book_id", None)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="حالا می‌تونی از منو «🚀 فعال‌سازی کتاب» رو بزنی.",
        reply_markup=ADMIN_MENU,
    )
    return ConversationHandler.END


schedule_conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^📅 تعیین برنامه همخوانی$"), schedule_start)],
    states={
        CHOOSE_BOOK: [CallbackQueryHandler(schedule_choose_book, pattern="^sched_book:")],
        ASK_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, schedule_ask_date)],
        ASK_BOOK_PAGES: [MessageHandler(filters.TEXT & ~filters.COMMAND, schedule_ask_book_pages)],
        ASK_PDF_PAGES: [MessageHandler(filters.TEXT & ~filters.COMMAND, schedule_ask_pdf_pages)],
        ASK_CONTINUE: [CallbackQueryHandler(schedule_continue_or_done, pattern="^sched:")],
    },
    fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
)
