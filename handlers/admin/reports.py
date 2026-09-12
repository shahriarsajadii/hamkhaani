# -*- coding: utf-8 -*-
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
from utils.keyboards import books_kb, reading_days_kb, questions_kb
from utils.jalali import parse_jalali, format_jalali_human
from utils.formatting import format_day_report, format_question_report
from handlers.common import is_admin

CHOOSE_BOOK_DAY, CHOOSE_DAY = range(2)
CHOOSE_BOOK_Q, CHOOSE_QUESTION = range(2, 4)

STATUS_LABELS = {"draft": "پیش‌نویس", "active": "فعال", "finished": "پایان‌یافته"}


# ------------------------------------------------------------ لیست کتاب‌ها --

async def list_books_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    books = db.list_books()
    if not books:
        await update.message.reply_text("هنوز کتابی ثبت نشده.")
        return
    lines = ["📚 لیست کتاب‌ها:\n"]
    for b in books:
        lines.append(f"#{b['id']} - {b['title']} ({STATUS_LABELS.get(b['status'], b['status'])})")
    await update.message.reply_text("\n".join(lines))


# --------------------------------------------------------------- گزارش روز --

async def day_report_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END
    books = db.list_books(status="active")
    if not books:
        await update.message.reply_text("کتاب فعالی وجود نداره.")
        return ConversationHandler.END
    await update.message.reply_text("گزارش کدوم کتاب رو می‌خوای؟", reply_markup=books_kb(books, "rep_book"))
    return CHOOSE_BOOK_DAY


async def day_report_choose_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    book_id = int(query.data.split(":")[1])
    days = db.get_reading_days(book_id)
    if not days:
        await query.edit_message_text("این کتاب برنامه‌ای نداره.")
        return ConversationHandler.END
    await query.edit_message_text("گزارش کدوم روز؟", reply_markup=reading_days_kb(days, "rep_day"))
    return CHOOSE_DAY


async def day_report_choose_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    reading_day_id = int(query.data.split(":")[1])
    rday = db.get_reading_day(reading_day_id)
    rows = db.get_progress_for_day(reading_day_id)
    jd = parse_jalali(rday["jalali_date"])
    text = format_day_report(format_jalali_human(jd), rows)
    await query.edit_message_text(text)
    return ConversationHandler.END


day_report_conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^📊 گزارش روز$"), day_report_start)],
    states={
        CHOOSE_BOOK_DAY: [CallbackQueryHandler(day_report_choose_book, pattern="^rep_book:")],
        CHOOSE_DAY: [CallbackQueryHandler(day_report_choose_day, pattern="^rep_day:")],
    },
    fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
)


# ----------------------------------------------------------- گزارش سوالات --

async def question_report_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END
    books = db.list_books()
    books_with_q = [b for b in books if db.get_questions(b["id"])]
    if not books_with_q:
        await update.message.reply_text("هیچ کتابی سوال ثبت‌شده نداره.")
        return ConversationHandler.END
    await update.message.reply_text(
        "گزارش سوالات کدوم کتاب؟", reply_markup=books_kb(books_with_q, "qrep_book")
    )
    return CHOOSE_BOOK_Q


async def question_report_choose_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    book_id = int(query.data.split(":")[1])
    questions = db.get_questions(book_id)
    await query.edit_message_text("کدوم سوال؟", reply_markup=questions_kb(questions, "qrep_q"))
    return CHOOSE_QUESTION


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


question_report_conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^📋 گزارش سوالات$"), question_report_start)],
    states={
        CHOOSE_BOOK_Q: [CallbackQueryHandler(question_report_choose_book, pattern="^qrep_book:")],
        CHOOSE_QUESTION: [
            CallbackQueryHandler(question_report_choose_question, pattern="^qrep_q:")
        ],
    },
    fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
)
