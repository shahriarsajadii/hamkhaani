# -*- coding: utf-8 -*-
"""
کاربر بعد از تمام‌کردن کتاب، وارد این مسیر می‌شه و سوالات رو یکی‌یکی جواب می‌ده.
هر بار سوالی که هنوز جواب نداده رو نشون می‌دیم.
"""
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
from utils.keyboards import books_kb, USER_MENU, CANCEL_KB

CHOOSE_BOOK, ANSWERING = range(2)


async def answers_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    user_row = db.get_user_by_telegram_id(tg_user.id)
    if not user_row:
        await update.message.reply_text("اول باید توی یه کتاب ثبت‌نام کنی.")
        return ConversationHandler.END

    books = db.get_user_books(user_row["id"])
    books_with_q = [b for b in books if db.get_questions(b["id"])]
    if not books_with_q:
        await update.message.reply_text("هنوز سوالی برای کتاب‌های تو تعریف نشده.")
        return ConversationHandler.END

    await update.message.reply_text(
        "می‌خوای به سوالات کدوم کتاب جواب بدی؟", reply_markup=books_kb(books_with_q, "ans_book")
    )
    return CHOOSE_BOOK


async def _send_next_question(update_or_query, context, book_id, user_id):
    questions = db.get_questions(book_id)
    for q in questions:
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

    tg_user = update.effective_user
    user_row = db.get_user_by_telegram_id(tg_user.id)
    context.user_data["ans_user_id"] = user_row["id"]

    has_next = await _send_next_question(query, context, book_id, user_row["id"])
    if not has_next:
        await query.edit_message_text("🎉 تو به همه‌ی سوالات این کتاب جواب دادی!")
        return ConversationHandler.END
    return ANSWERING


async def answers_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question_id = context.user_data.get("ans_question_id")
    user_id = context.user_data.get("ans_user_id")
    book_id = context.user_data.get("ans_book_id")
    if not question_id or not user_id:
        await update.message.reply_text("مشکلی پیش اومد، دوباره از منو شروع کن.", reply_markup=USER_MENU)
        return ConversationHandler.END

    text = update.message.text.strip()
    db.save_answer(question_id, user_id, text)

    has_next = await _send_next_question(update.message, context, book_id, user_id)
    if not has_next:
        await update.message.reply_text("🎉 تو به همه‌ی سوالات این کتاب جواب دادی! ممنون بابت وقتی که گذاشتی.", reply_markup=USER_MENU)
        context.user_data.pop("ans_book_id", None)
        context.user_data.pop("ans_question_id", None)
        context.user_data.pop("ans_user_id", None)
        return ConversationHandler.END
    return ANSWERING


answers_conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^📝 پاسخ به سوالات$"), answers_start)],
    states={
        CHOOSE_BOOK: [CallbackQueryHandler(answers_choose_book, pattern="^ans_book:")],
        ANSWERING: [MessageHandler(filters.TEXT & ~filters.COMMAND, answers_receive)],
    },
    fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
)
