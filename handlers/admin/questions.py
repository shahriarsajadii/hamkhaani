# -*- coding: utf-8 -*-
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
)

import database as db
from utils.keyboards import (
    books_kb,
    question_manage_kb,
    question_actions_kb,
    confirm_delete_question_kb,
    BTN_QUESTIONS,
)
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


def _question_list_text(book, questions) -> str:
    if not questions:
        return f"📖 «{book['title']}»\n\nهنوز سوالی برای این کتاب ثبت نشده."
    lines = [f"📖 «{book['title']}»", "", "سوالات ثبت‌شده:"]
    for q in questions:
        lines.append(f"{q['order_index']}. {q['text']}")
    lines.append("")
    lines.append("برای ویرایش یا حذف، سوال موردنظر را انتخاب کن.")
    return "\n".join(lines)


async def questions_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END
    context.user_data.clear()
    books = db.list_books()
    if not books:
        return await end_and_show_menu(update, context, "هنوز هیچ کتابی ثبت نشده.")
    await update.message.reply_text(
        "برای کدوم کتاب می‌خوای سوالاتش رو مدیریت کنی؟",
        reply_markup=books_kb(books, "q_book"),
    )
    return S.Q_CHOOSE_BOOK


async def questions_choose_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        book_id = int(query.data.split(":")[1])
    except (IndexError, ValueError):
        await query.edit_message_text("شناسه کتاب نامعتبر است.")
        return ConversationHandler.END

    book = db.get_book(book_id)
    if not book:
        await query.edit_message_text("کتاب پیدا نشد.")
        return ConversationHandler.END

    context.user_data["q_book_id"] = book_id
    questions = db.get_questions(book_id)
    context.user_data["q_next_index"] = (
        max(q["order_index"] for q in questions) + 1 if questions else 1
    )

    await query.edit_message_text(
        _question_list_text(book, questions),
        reply_markup=question_manage_kb(questions),
    )
    return S.Q_MANAGE_LIST


async def questions_manage_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # مثلاً q_action:add یا q_action:done یا q_action:back
    parts = query.data.split(":")
    # parts[0] = "q_action", parts[1] = "add"/"done"/"back"
    action = parts[1] if len(parts) > 1 else ""

    if action == "add":
        await query.edit_message_text(
            "متن سوال جدید رو بفرست:",
            reply_markup=None,
        )
        return S.Q_ASK_TEXT

    if action == "done":
        return await _finish_questions(query, context)

    if action == "back":
        book = db.get_book(context.user_data.get("q_book_id"))
        if not book:
            return await _finish_questions(query, context)
        questions = db.get_questions(book["id"])
        await query.edit_message_text(
            _question_list_text(book, questions),
            reply_markup=question_manage_kb(questions),
        )
        return S.Q_MANAGE_LIST

    return S.Q_MANAGE_LIST


async def questions_select_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    question_id = int(query.data.split(":")[1])
    question = db.get_question(question_id)
    if not question:
        await query.edit_message_text("این سوال پیدا نشد.")
        return S.Q_MANAGE_LIST

    context.user_data["q_selected_id"] = question_id
    await query.edit_message_text(
        f"❓ سوال {question['order_index']}:\n\n{question['text']}",
        reply_markup=question_actions_kb(question_id),
    )
    return S.Q_MANAGE_ITEM


async def questions_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "q_action:back":
        book_id = context.user_data.get("q_book_id")
        book = db.get_book(book_id) if book_id else None
        questions = db.get_questions(book_id) if book else []
        if not book:
            return await _finish_questions(query, context)
        await query.edit_message_text(
            _question_list_text(book, questions),
            reply_markup=question_manage_kb(questions),
        )
        return S.Q_MANAGE_LIST

    question_id = int(query.data.split(":")[1])
    question = db.get_question(question_id)
    if not question:
        await query.edit_message_text("این سوال پیدا نشد.")
        return S.Q_MANAGE_LIST

    context.user_data["q_selected_id"] = question_id

    if query.data.startswith("q_edit:"):
        await query.edit_message_text(
            f"متن جدید سوال {question['order_index']} رو بفرست:"
        )
        return S.Q_EDIT_TEXT

    if query.data.startswith("q_delete:"):
        await query.edit_message_text(
            f"⚠️ مطمئنی سوال زیر حذف بشه؟\n\n{question['text']}",
            reply_markup=confirm_delete_question_kb(question_id),
        )
        return S.Q_DELETE_CONFIRM

    return S.Q_MANAGE_ITEM


async def questions_edit_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question_id = context.user_data.get("q_selected_id")
    book_id = context.user_data.get("q_book_id")
    text = update.message.text.strip()

    if not question_id or not book_id:
        return await end_and_show_menu(
            update, context, "مشکلی پیش اومد، دوباره از منو شروع کن."
        )

    if not text:
        await update.message.reply_text("متن سوال نمی‌تواند خالی باشد.")
        return S.Q_EDIT_TEXT

    db.update_question(question_id, text)
    book = db.get_book(book_id)
    questions = db.get_questions(book_id)
    await update.message.reply_text(
        "✅ سوال ویرایش شد.\n\n" + _question_list_text(book, questions),
        reply_markup=question_manage_kb(questions),
    )
    context.user_data["q_next_index"] = (
        max(q["order_index"] for q in questions) + 1 if questions else 1
    )
    return S.Q_MANAGE_LIST


async def questions_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, answer, question_id = query.data.split(":")
    question_id = int(question_id)
    book_id = context.user_data.get("q_book_id")

    if answer == "yes":
        db.delete_question(question_id)
        message = "✅ سوال حذف شد."
    else:
        message = "↩️ حذف سوال لغو شد."

    book = db.get_book(book_id)
    questions = db.get_questions(book_id) if book else []
    if not book:
        return await _finish_questions(query, context)

    await query.edit_message_text(
        message + "\n\n" + _question_list_text(book, questions),
        reply_markup=question_manage_kb(questions),
    )
    context.user_data["q_next_index"] = (
        max(q["order_index"] for q in questions) + 1 if questions else 1
    )
    return S.Q_MANAGE_LIST


async def questions_ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    book_id = context.user_data.get("q_book_id")
    if not book_id:
        return await end_and_show_menu(
            update, context, "مشکلی پیش اومد، دوباره از منو شروع کن."
        )

    text = update.message.text.strip()
    if not text:
        await update.message.reply_text("متن سوال نمی‌تواند خالی باشد.")
        return S.Q_ASK_TEXT

    idx = context.user_data["q_next_index"]
    db.add_question(book_id, idx, text)
    context.user_data["q_next_index"] = idx + 1

    await update.message.reply_text(
        f"✅ سوال {idx} ثبت شد. سوال بعدی رو اضافه کنم؟",
        reply_markup=CONTINUE_KB,
    )
    return S.Q_CONTINUE


async def questions_continue_or_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "q:more":
        await query.edit_message_text("متن سوال بعدی رو بفرست:")
        return S.Q_ASK_TEXT

    book_id = context.user_data.get("q_book_id")
    book = db.get_book(book_id)
    questions = db.get_questions(book_id) if book else []

    if book:
        await query.edit_message_text(
            _question_list_text(book, questions),
            reply_markup=question_manage_kb(questions),
        )
        return S.Q_MANAGE_LIST

    return await _finish_questions(query, context)


async def _finish_questions(query, context):
    context.user_data.clear()
    await query.edit_message_text("✅ مدیریت سوالات تمام شد.")
    return ConversationHandler.END


ENTRY_POINTS = [MessageHandler(button_filter(BTN_QUESTIONS), questions_start)]

STATES = {
    S.Q_CHOOSE_BOOK: [
        CallbackQueryHandler(questions_choose_book, pattern="^q_book:")
    ],
    S.Q_MANAGE_LIST: [
        CallbackQueryHandler(questions_manage_list, pattern="^q_action:"),
        CallbackQueryHandler(questions_select_item, pattern="^q_item:"),
    ],
    S.Q_MANAGE_ITEM: [
        CallbackQueryHandler(questions_action, pattern="^(q_(edit|delete):|q_action:back$)")
    ],
    S.Q_EDIT_TEXT: [MessageHandler(TEXT_INPUT, questions_edit_text)],
    S.Q_DELETE_CONFIRM: [
        CallbackQueryHandler(questions_delete_confirm, pattern="^q_delconfirm:")
    ],
    S.Q_ASK_TEXT: [MessageHandler(TEXT_INPUT, questions_ask_question)],
    S.Q_CONTINUE: [CallbackQueryHandler(questions_continue_or_done, pattern="^q:")],
}