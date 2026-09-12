# -*- coding: utf-8 -*-
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
)

import database as db
from utils.keyboards import books_kb, BTN_QUESTIONS
from handlers.common import is_admin, TEXT_INPUT, end_and_show_menu, button_filter
from handlers.states import S

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
    context.user_data.clear()
    books = db.list_books()
    if not books:
        return await end_and_show_menu(update, context, "هنوز هیچ کتابی ثبت نشده.")
    await update.message.reply_text(
        "برای کدوم کتاب می‌خوای سوال تعریف کنی؟", reply_markup=books_kb(books, "q_book")
    )
    return S.Q_CHOOSE_BOOK


async def questions_choose_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    book_id = int(query.data.split(":")[1])
    context.user_data["q_book_id"] = book_id
    existing = db.get_questions(book_id)
    context.user_data["q_next_index"] = (existing[-1]["order_index"] + 1) if existing else 1
    await query.edit_message_text("متن سوال رو بفرست:")
    return S.Q_ASK_TEXT


async def questions_ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    book_id = context.user_data.get("q_book_id")
    if not book_id:
        return await end_and_show_menu(update, context, "مشکلی پیش اومد، دوباره از منو شروع کن.")
    idx = context.user_data["q_next_index"]
    db.add_question(book_id, idx, update.message.text.strip())
    context.user_data["q_next_index"] = idx + 1
    await update.message.reply_text(
        f"✅ سوال {idx} ثبت شد. سوال بعدی رو اضافه کنم؟", reply_markup=CONTINUE_KB
    )
    return S.Q_CONTINUE


async def questions_continue_or_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "q:more":
        await query.edit_message_text("متن سوال بعدی رو بفرست:")
        return S.Q_ASK_TEXT

    await query.edit_message_text("✅ سوالات این کتاب ثبت شد.")
    return await end_and_show_menu(update, context, "برگشتیم به منو 👇")


ENTRY_POINTS = [MessageHandler(button_filter(BTN_QUESTIONS), questions_start)]

STATES = {
    S.Q_CHOOSE_BOOK: [CallbackQueryHandler(questions_choose_book, pattern="^q_book:")],
    S.Q_ASK_TEXT: [MessageHandler(TEXT_INPUT, questions_ask_question)],
    S.Q_CONTINUE: [CallbackQueryHandler(questions_continue_or_done, pattern="^q:")],
}
