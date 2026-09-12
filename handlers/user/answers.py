# -*- coding: utf-8 -*-
"""
کاربر بعد از تمام‌کردن کتاب، وارد این مسیر می‌شه و سوالات رو یکی‌یکی جواب می‌ده.
هر بار سوالی که هنوز جواب نداده رو نشون می‌دیم.
"""
from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
)

import database as db
from utils.keyboards import books_kb, CANCEL_KB, BTN_ANSWER_QUESTIONS
from handlers.common import TEXT_INPUT, end_and_show_menu, button_filter
from handlers.states import S


async def answers_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    user_row = db.get_user_by_telegram_id(update.effective_user.id)
    if not user_row:
        return await end_and_show_menu(update, context, "اول باید توی یه کتاب ثبت‌نام کنی.")

    books = db.get_user_books(user_row["id"])
    books_with_q = [b for b in books if db.get_questions(b["id"])]
    if not books_with_q:
        return await end_and_show_menu(update, context, "هنوز سوالی برای کتاب‌های تو تعریف نشده.")

    await update.message.reply_text(
        "می‌خوای به سوالات کدوم کتاب جواب بدی؟", reply_markup=books_kb(books_with_q, "ans_book")
    )
    return S.ANS_CHOOSE_BOOK


async def _send_next_question(update_or_query, context, book_id, user_id):
    for q in db.get_questions(book_id):
        if not db.has_answered(q["id"], user_id):
            context.user_data["ans_question_id"] = q["id"]
            text = f"❓ سوال {q['order_index']}:\n{q['text']}\n\nجوابت رو بنویس:"
            if hasattr(update_or_query, "edit_message_text"):
                await update_or_query.edit_message_text(text)
            else:
                await update_or_query.reply_text(text, reply_markup=CANCEL_KB)
            return True
    return False


async def answers_choose_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    book_id = int(query.data.split(":")[1])
    context.user_data["ans_book_id"] = book_id

    user_row = db.get_user_by_telegram_id(update.effective_user.id)
    context.user_data["ans_user_id"] = user_row["id"]

    has_next = await _send_next_question(query, context, book_id, user_row["id"])
    if not has_next:
        await query.edit_message_text("🎉 تو به همه‌ی سوالات این کتاب جواب دادی!")
        return ConversationHandler.END
    return S.ANS_ANSWERING


async def answers_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question_id = context.user_data.get("ans_question_id")
    user_id = context.user_data.get("ans_user_id")
    book_id = context.user_data.get("ans_book_id")
    if not question_id or not user_id:
        return await end_and_show_menu(update, context, "مشکلی پیش اومد، دوباره از منو شروع کن.")

    db.save_answer(question_id, user_id, update.message.text.strip())

    has_next = await _send_next_question(update.message, context, book_id, user_id)
    if not has_next:
        return await end_and_show_menu(
            update, context, "🎉 تو به همه‌ی سوالات این کتاب جواب دادی! ممنون بابت وقتی که گذاشتی."
        )
    return S.ANS_ANSWERING


ENTRY_POINTS = [MessageHandler(button_filter(BTN_ANSWER_QUESTIONS), answers_start)]

STATES = {
    S.ANS_CHOOSE_BOOK: [CallbackQueryHandler(answers_choose_book, pattern="^ans_book:")],
    S.ANS_ANSWERING: [MessageHandler(TEXT_INPUT, answers_receive)],
}
