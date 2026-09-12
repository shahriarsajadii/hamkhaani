# -*- coding: utf-8 -*-
"""
برنامه همخوانی یک کتاب.

ادمین کتاب را انتخاب می‌کند و اگر برنامه‌ای داشته باشد، همان اول کامل نمایش داده می‌شود.
بعد می‌تواند:
  - «✏️ ویرایش برنامه»: تاریخ شروع و تعداد صفحه در روز را بدهد و برنامه بر اساس
    تعداد کل صفحات کتاب خودکار ساخته شود (صفحات پی‌دی‌اف به تناسب محاسبه می‌شوند).
  - «✍️ ورود دستی روزها»: روزها را یکی‌یکی دستی وارد کند.
"""
import re

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
)

import database as db
from utils.keyboards import books_kb, BTN_SCHEDULE
from utils.jalali import parse_jalali, to_gregorian, days_with_human
from utils.formatting import format_schedule_days
from utils.schedule import generate_days
from handlers.common import is_admin, TEXT_INPUT, end_and_show_menu, button_filter
from handlers.states import S

SCHEDULE_ACTIONS_KB = InlineKeyboardMarkup(
    [
        [InlineKeyboardButton("✏️ ویرایش برنامه (ساخت خودکار)", callback_data="sched:auto")],
        [InlineKeyboardButton("✍️ ورود دستی روزها", callback_data="sched:manual")],
    ]
)

MANUAL_CONTINUE_KB = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("➕ افزودن روز بعد", callback_data="schedm:more"),
            InlineKeyboardButton("✅ پایان و ذخیره", callback_data="schedm:done"),
        ]
    ]
)

CONFIRM_KB = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("✅ ذخیره برنامه", callback_data="schedc:save"),
            InlineKeyboardButton("↩️ انصراف", callback_data="schedc:cancel"),
        ]
    ]
)


def _extract_two_numbers(text: str):
    nums = re.findall(r"\d+", text)
    if len(nums) < 2:
        raise ValueError("باید دو عدد بفرستی، مثلا: 1 تا 30")
    return int(nums[0]), int(nums[1])


def _schedule_text(book_id: int) -> str:
    days = db.get_reading_days(book_id)
    if not days:
        return "برای این کتاب هنوز برنامه‌ای ثبت نشده."
    return format_schedule_days(days_with_human(days))


async def schedule_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END
    context.user_data.clear()
    books = db.list_books()
    if not books:
        return await end_and_show_menu(update, context, "هنوز کتابی ثبت نشده.")
    await update.message.reply_text(
        "برنامه‌ی کدوم کتاب؟", reply_markup=books_kb(books, "sched_book")
    )
    return S.SCHED_CHOOSE_BOOK


async def schedule_choose_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    book_id = int(query.data.split(":")[1])
    context.user_data["sched_book_id"] = book_id
    book = db.get_book(book_id)

    await query.edit_message_text(
        f"📖 «{book['title']}»\n\n{_schedule_text(book_id)}",
        reply_markup=SCHEDULE_ACTIONS_KB,
    )
    return S.SCHED_ACTION


async def schedule_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data.split(":")[1]

    if action == "manual":
        context.user_data["sched_days"] = []
        await query.edit_message_text("تاریخ روز اول رو به فرمت 1403/06/21 بفرست:")
        return S.SCHED_MANUAL_DATE

    book = db.get_book(context.user_data["sched_book_id"])
    if not book["book_pages"]:
        await query.edit_message_text(
            "⚠️ برای ساخت خودکار برنامه، اول باید تعداد صفحات کتاب رو از «✏️ ویرایش کتاب» ثبت کنی."
        )
        return await end_and_show_menu(update, context, "برگشتیم به منو 👇")

    await query.edit_message_text("تاریخ شروع همخوانی رو به فرمت 1403/06/21 بفرست:")
    return S.SCHED_ASK_START_DATE


# --------------------------------------------------------- ساخت خودکار --

async def schedule_ask_start_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        parse_jalali(update.message.text)
    except ValueError as e:
        await update.message.reply_text(f"تاریخ نامعتبره: {e}\nدوباره امتحان کن (مثال: 1403/06/21)")
        return S.SCHED_ASK_START_DATE

    context.user_data["sched_start_date"] = update.message.text.strip()
    await update.message.reply_text("روزی چند صفحه کتاب خونده بشه؟ (مثال: 30)")
    return S.SCHED_ASK_PAGES_PER_DAY


async def schedule_ask_pages_per_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        pages_per_day = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("باید یه عدد بفرستی، مثلا: 30")
        return S.SCHED_ASK_PAGES_PER_DAY

    book = db.get_book(context.user_data["sched_book_id"])
    try:
        days = generate_days(
            parse_jalali(context.user_data["sched_start_date"]),
            pages_per_day,
            book["book_pages"],
            book["pdf_pages"],
        )
    except ValueError as e:
        await update.message.reply_text(str(e))
        return S.SCHED_ASK_PAGES_PER_DAY

    context.user_data["sched_generated"] = days
    await update.message.reply_text(
        f"📖 «{book['title']}» - {len(days)} روز\n\n" + format_schedule_days(days_with_human(days)),
        reply_markup=CONFIRM_KB,
    )
    return S.SCHED_CONFIRM


async def schedule_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data.split(":")[1] != "save":
        await query.edit_message_text("انصراف داده شد، برنامه‌ی قبلی دست‌نخورده موند.")
        return await end_and_show_menu(update, context, "برگشتیم به منو 👇")

    book_id = context.user_data["sched_book_id"]
    db.replace_reading_days(book_id, context.user_data["sched_generated"])
    await query.edit_message_text(
        "✅ برنامه ذخیره شد:\n\n" + _schedule_text(book_id)
    )
    return await end_and_show_menu(
        update, context, "حالا می‌تونی از منو «🚀 فعال‌سازی کتاب» رو بزنی."
    )


# ----------------------------------------------------------- ورود دستی --

async def schedule_manual_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        parse_jalali(text)
    except ValueError as e:
        await update.message.reply_text(f"تاریخ نامعتبره: {e}\nدوباره امتحان کن (مثال: 1403/06/21)")
        return S.SCHED_MANUAL_DATE
    context.user_data["sched_current_date"] = text
    await update.message.reply_text("بازه صفحات کتاب رو بفرست (مثال: 1 تا 30):")
    return S.SCHED_MANUAL_BOOK_PAGES


async def schedule_manual_book_pages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        f, t = _extract_two_numbers(update.message.text)
    except ValueError as e:
        await update.message.reply_text(str(e))
        return S.SCHED_MANUAL_BOOK_PAGES
    context.user_data["sched_book_from"] = f
    context.user_data["sched_book_to"] = t
    await update.message.reply_text("بازه صفحات پی‌دی‌اف رو بفرست (مثال: 3 تا 15):")
    return S.SCHED_MANUAL_PDF_PAGES


async def schedule_manual_pdf_pages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        f, t = _extract_two_numbers(update.message.text)
    except ValueError as e:
        await update.message.reply_text(str(e))
        return S.SCHED_MANUAL_PDF_PAGES

    jalali_date = context.user_data.pop("sched_current_date")
    context.user_data["sched_days"].append(
        {
            "jalali_date": jalali_date,
            "gregorian_date": to_gregorian(parse_jalali(jalali_date)).isoformat(),
            "book_page_from": context.user_data.pop("sched_book_from"),
            "book_page_to": context.user_data.pop("sched_book_to"),
            "pdf_page_from": f,
            "pdf_page_to": t,
        }
    )
    await update.message.reply_text(
        f"روز {len(context.user_data['sched_days'])} ثبت موقت شد ✅\nادامه بدم یا تمومه؟",
        reply_markup=MANUAL_CONTINUE_KB,
    )
    return S.SCHED_MANUAL_CONTINUE


async def schedule_manual_continue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.split(":")[1] == "more":
        await query.edit_message_text("تاریخ روز بعد رو به فرمت 1403/06/21 بفرست:")
        return S.SCHED_MANUAL_DATE

    book_id = context.user_data["sched_book_id"]
    db.replace_reading_days(book_id, context.user_data["sched_days"])
    await query.edit_message_text("✅ برنامه ذخیره شد:\n\n" + _schedule_text(book_id))
    return await end_and_show_menu(
        update, context, "حالا می‌تونی از منو «🚀 فعال‌سازی کتاب» رو بزنی."
    )


ENTRY_POINTS = [MessageHandler(button_filter(BTN_SCHEDULE), schedule_start)]

STATES = {
    S.SCHED_CHOOSE_BOOK: [CallbackQueryHandler(schedule_choose_book, pattern="^sched_book:")],
    S.SCHED_ACTION: [CallbackQueryHandler(schedule_action, pattern="^sched:")],
    S.SCHED_ASK_START_DATE: [MessageHandler(TEXT_INPUT, schedule_ask_start_date)],
    S.SCHED_ASK_PAGES_PER_DAY: [MessageHandler(TEXT_INPUT, schedule_ask_pages_per_day)],
    S.SCHED_CONFIRM: [CallbackQueryHandler(schedule_confirm, pattern="^schedc:")],
    S.SCHED_MANUAL_DATE: [MessageHandler(TEXT_INPUT, schedule_manual_date)],
    S.SCHED_MANUAL_BOOK_PAGES: [MessageHandler(TEXT_INPUT, schedule_manual_book_pages)],
    S.SCHED_MANUAL_PDF_PAGES: [MessageHandler(TEXT_INPUT, schedule_manual_pdf_pages)],
    S.SCHED_MANUAL_CONTINUE: [CallbackQueryHandler(schedule_manual_continue, pattern="^schedm:")],
}
