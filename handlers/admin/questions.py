# -*- coding: utf-8 -*-
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

import database as db
from utils.keyboards import books_kb, ADMIN_MENU
from handlers.common import is_admin

CHOOSE_BOOK, ASK_QUESTION, ASK_CONTINUE = range(3)

CONTINUE_KB = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("➕ سوال بعدی", callback_data="q:more"),
            InlineKeyboardButton("✅ پایان", callback_data="q:done"),
        ]
    ]
)


async def questions_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END
    books = db.list_books()
    if not books:
        await update.message.reply_text("هنوز هیچ کتابی ثبت نشده.")
        return ConversationHandler.END
    await update.message.reply_text(
        "برای کدوم کتاب می‌خوای سوال تعریف کنی؟", reply_markup=books_kb(books, "q_book")
    )
    return CHOOSE_BOOK


async def questions_choose_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    book_id = int(query.data.split(":")[1])
    context.user_data["q_book_id"] = book_id
    existing = db.get_questions(book_id)
    context.user_data["q_next_index"] = (existing[-1]["order_index"] + 1) if existing else 1
    await query.edit_message_text("متن سوال رو بفرست:")
    return ASK_QUESTION


async def questions_ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    book_id = context.user_data["q_book_id"]
    idx = context.user_data["q_next_index"]
    db.add_question(book_id, idx, text)
    context.user_data["q_next_index"] = idx + 1
    await update.message.reply_text(
        f"✅ سوال {idx} ثبت شد. سوال بعدی رو اضافه کنم؟", reply_markup=CONTINUE_KB
    )
    return ASK_CONTINUE


async def questions_continue_or_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "q:more":
        await query.edit_message_text("متن سوال بعدی رو بفرست:")
        return ASK_QUESTION

    await query.edit_message_text("✅ سوالات این کتاب ثبت شد.")
    context.user_data.pop("q_book_id", None)
    context.user_data.pop("q_next_index", None)
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text="برگشتیم به منو 👇", reply_markup=ADMIN_MENU
    )
    return ConversationHandler.END


questions_conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^❓ تعیین سوالات کتاب$"), questions_start)],
    states={
        CHOOSE_BOOK: [CallbackQueryHandler(questions_choose_book, pattern="^q_book:")],
        ASK_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, questions_ask_question)],
        ASK_CONTINUE: [CallbackQueryHandler(questions_continue_or_done, pattern="^q:")],
    },
    fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
)
