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
from utils.keyboards import books_kb, USER_MENU

CHOOSE_BOOK = 1
STATUS_LABELS = {"draft": "پیش‌نویس", "active": "در حال خواندن", "finished": "پایان‌یافته"}


async def registration_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    books = db.list_books(status="active")
    if not books:
        await update.message.reply_text("در حال حاضر کتاب فعالی برای ثبت‌نام نیست.")
        return ConversationHandler.END
    await update.message.reply_text(
        "توی کدوم کتاب می‌خوای ثبت‌نام کنی؟", reply_markup=books_kb(books, "reg")
    )
    return CHOOSE_BOOK


async def registration_choose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    book_id = int(query.data.split(":")[1])
    book = db.get_book(book_id)

    tg_user = update.effective_user
    db.upsert_user(tg_user.id, tg_user.username, tg_user.full_name)
    user_row = db.get_user_by_telegram_id(tg_user.id)

    created = db.register_user_to_book(book_id, user_row["id"])
    if created:
        await query.edit_message_text(f"✅ توی کتاب «{book['title']}» ثبت‌نام شدی. موفق باشی 📖")
    else:
        await query.edit_message_text(f"قبلاً توی کتاب «{book['title']}» ثبت‌نام کرده بودی.")
    return ConversationHandler.END


registration_conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^📚 کتاب‌های فعال$"), registration_start)],
    states={CHOOSE_BOOK: [CallbackQueryHandler(registration_choose, pattern="^reg:")]},
    fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
)


async def my_books_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    user_row = db.get_user_by_telegram_id(tg_user.id)
    if not user_row:
        await update.message.reply_text("هنوز توی هیچ کتابی ثبت‌نام نکردی.")
        return
    books = db.get_user_books(user_row["id"])
    if not books:
        await update.message.reply_text("هنوز توی هیچ کتابی ثبت‌نام نکردی.")
        return
    lines = ["📖 کتاب‌های تو:\n"]
    for b in books:
        lines.append(f"- {b['title']} ({STATUS_LABELS.get(b['status'], b['status'])})")
    await update.message.reply_text("\n".join(lines), reply_markup=USER_MENU)
