# -*- coding: utf-8 -*-
from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
)

import database as db
from utils.keyboards import (
    books_kb,
    reading_days_kb,
    questions_kb,
    BTN_DAY_REPORT,
    BTN_QUESTION_REPORT,
    BTN_ANSWERS_REPORT,
    BTN_LIST_BOOKS,
)
from utils.jalali import parse_jalali, format_jalali_human
from utils.formatting import format_day_report, format_question_report, format_answers_report
from handlers.common import is_admin, end_and_show_menu, button_filter
from handlers.states import S

STATUS_LABELS = {"draft": "پیش‌نویس", "active": "فعال", "finished": "پایان‌یافته"}


# ------------------------------------------------------------ لیست کتاب‌ها --

async def list_books_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END
    context.user_data.clear()
    books = db.list_books()
    if not books:
        return await end_and_show_menu(update, context, "هنوز کتابی ثبت نشده.")
    lines = ["📚 لیست کتاب‌ها:\n"]
    for b in books:
        pages = f"{b['book_pages'] or '—'} صفحه کتاب / {b['pdf_pages'] or '—'} صفحه پی‌دی‌اف"
        lines.append(
            f"#{b['id']} - {b['title']} ({STATUS_LABELS.get(b['status'], b['status'])})\n   {pages}"
        )
    return await end_and_show_menu(update, context, "\n".join(lines))


# --------------------------------------------------------------- گزارش روز --

async def day_report_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END
    context.user_data.clear()
    books = db.list_books(status="active")
    if not books:
        return await end_and_show_menu(update, context, "کتاب فعالی وجود نداره.")
    await update.message.reply_text(
        "گزارش کدوم کتاب رو می‌خوای؟", reply_markup=books_kb(books, "rep_book")
    )
    return S.DAYREP_CHOOSE_BOOK


async def day_report_choose_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    book_id = int(query.data.split(":")[1])
    days = db.get_reading_days(book_id)
    if not days:
        await query.edit_message_text("این کتاب برنامه‌ای نداره.")
        return ConversationHandler.END
    await query.edit_message_text("گزارش کدوم روز؟", reply_markup=reading_days_kb(days, "rep_day"))
    return S.DAYREP_CHOOSE_DAY


async def day_report_choose_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    reading_day_id = int(query.data.split(":")[1])
    rday = db.get_reading_day(reading_day_id)
    rows = db.get_progress_for_day(reading_day_id)
    jd = parse_jalali(rday["jalali_date"])
    await query.edit_message_text(format_day_report(format_jalali_human(jd), rows))
    return ConversationHandler.END


# ----------------------------------------------------------- گزارش سوالات --

async def question_report_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END
    context.user_data.clear()
    books_with_q = [b for b in db.list_books() if db.get_questions(b["id"])]
    if not books_with_q:
        return await end_and_show_menu(update, context, "هیچ کتابی سوال ثبت‌شده نداره.")
    await update.message.reply_text(
        "گزارش سوالات کدوم کتاب؟", reply_markup=books_kb(books_with_q, "qrep_book")
    )
    return S.QREP_CHOOSE_BOOK


async def question_report_choose_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    book_id = int(query.data.split(":")[1])
    questions = db.get_questions(book_id)
    await query.edit_message_text("کدوم سوال؟", reply_markup=questions_kb(questions, "qrep_q"))
    return S.QREP_CHOOSE_QUESTION


async def question_report_choose_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    question_id = int(query.data.split(":")[1])
    question = db.get_question(question_id)
    answers = db.get_answers_for_question(question_id)
    text = format_question_report(question["text"], answers)
    # اگه پیام خیلی بلند باشه تلگرام ارور میده، پس تکه‌تکه می‌فرستیم
    if len(text) > 3500:
        await query.edit_message_text(f"❓ {question['text']}\n(گزارش کامل در پیام‌های بعدی)")
        chunk = ""
        for line in text.splitlines():
            if len(chunk) + len(line) > 3500:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=chunk)
                chunk = ""
            chunk += line + "\n"
        if chunk:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=chunk)
    else:
        await query.edit_message_text(text)
    return ConversationHandler.END


# --------------------------------------------------- گزارش جواب افراد --

async def answers_report_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END
    context.user_data.clear()
    books_with_q = [b for b in db.list_books() if db.get_questions(b["id"])]
    if not books_with_q:
        return await end_and_show_menu(update, context, "هیچ کتابی سوال ثبت‌شده نداره.")
    await update.message.reply_text(
        "گزارش جواب افراد برای کدوم کتاب؟",
        reply_markup=books_kb(books_with_q, "arep_book"),
    )
    return S.ANSWERS_REPORT_CHOOSE_BOOK


async def answers_report_choose_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    book_id = int(query.data.split(":")[1])
    book = db.get_book(book_id)
    if not book:
        await query.edit_message_text("کتاب پیدا نشد.")
        return ConversationHandler.END

    report_data = db.get_book_answers_report(book_id)
    if not report_data:
        await query.edit_message_text("هنوز کسی در این کتاب ثبت‌نام نکرده.")
        return ConversationHandler.END

    text = format_answers_report(book["title"], report_data)

    # ارسال تکه‌تکه اگر متن بلند بود
    if len(text) > 3500:
        await query.edit_message_text(f"📝 گزارش جواب افراد — «{book['title']}»\n(در پیام‌های بعدی ارسال می‌شود)")
        chunk = ""
        for line in text.splitlines():
            if len(chunk) + len(line) + 1 > 3500:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=chunk)
                chunk = ""
            chunk += line + "\n"
        if chunk.strip():
            await context.bot.send_message(chat_id=update.effective_chat.id, text=chunk)
    else:
        await query.edit_message_text(text)

    return ConversationHandler.END


ENTRY_POINTS = [
    MessageHandler(button_filter(BTN_DAY_REPORT), day_report_start),
    MessageHandler(button_filter(BTN_QUESTION_REPORT), question_report_start),
    MessageHandler(button_filter(BTN_ANSWERS_REPORT), answers_report_start),
    MessageHandler(button_filter(BTN_LIST_BOOKS), list_books_handler),
]

STATES = {
    S.DAYREP_CHOOSE_BOOK: [CallbackQueryHandler(day_report_choose_book, pattern="^rep_book:")],
    S.DAYREP_CHOOSE_DAY: [CallbackQueryHandler(day_report_choose_day, pattern="^rep_day:")],
    S.QREP_CHOOSE_BOOK: [CallbackQueryHandler(question_report_choose_book, pattern="^qrep_book:")],
    S.QREP_CHOOSE_QUESTION: [
        CallbackQueryHandler(question_report_choose_question, pattern="^qrep_q:")
    ],
    S.ANSWERS_REPORT_CHOOSE_BOOK: [
        CallbackQueryHandler(answers_report_choose_book, pattern="^arep_book:")
    ],
}