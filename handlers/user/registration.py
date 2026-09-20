# -*- coding: utf-8 -*-
from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
)

import logging

import database as db
from utils.keyboards import books_kb, BTN_ACTIVE_BOOKS, BTN_MY_BOOKS
from utils.formatting import format_members_list
from handlers.common import end_and_show_menu, button_filter
from handlers.states import S

logger = logging.getLogger(__name__)

STATUS_LABELS = {"draft": "پیش‌نویس", "active": "در حال خواندن", "finished": "پایان‌یافته"}


async def registration_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    books = db.list_books(status="active")
    if not books:
        return await end_and_show_menu(
            update, context, "در حال حاضر کتاب فعالی برای ثبت‌نام نیست."
        )
    await update.message.reply_text(
        "توی کدوم کتاب می‌خوای ثبت‌نام کنی؟", reply_markup=books_kb(books, "reg")
    )
    return S.REG_CHOOSE_BOOK


async def registration_choose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    book_id = int(query.data.split(":")[1])
    book = db.get_book(book_id)
    if not book:
        await query.edit_message_text("این کتاب دیگر وجود ندارد.")
        return ConversationHandler.END

    if book["status"] != "active":
        await query.edit_message_text(
            "این کتاب دیگر فعال نیست و ثبت‌نام در آن ممکن نیست."
        )
        return ConversationHandler.END

    tg_user = update.effective_user
    db.upsert_user(tg_user.id, tg_user.username, tg_user.full_name)
    user_row = db.get_user_by_telegram_id(tg_user.id)

    created = db.register_user_to_book(book_id, user_row["id"])
    if created:
        await query.edit_message_text(
            f"✅ توی کتاب «{book['title']}» ثبت‌نام شدی. موفق باشی 📖"
        )

        # آپدیت پیام لیست اعضا در تاپیک «پیگیری»
        book = dict(book)
        if book.get("group_chat_id"):
            try:
                members = db.get_registered_users(book_id)
                members_text = format_members_list(book["title"], members)

                if book.get("members_message_id"):
                    # آپدیت پیام موجود
                    await context.bot.edit_message_text(
                        chat_id=book["group_chat_id"],
                        message_id=book["members_message_id"],
                        text=members_text,
                    )
                else:
                    # اگه پیام قبلی ثبت نشده، یه پیام جدید بفرست و ذخیره کن
                    sent = await context.bot.send_message(
                        chat_id=book["group_chat_id"],
                        message_thread_id=book.get("topic_pigiri_id"),
                        text=members_text,
                    )
                    db.set_book_members_message_id(book_id, sent.message_id)
            except Exception as e:
                logger.warning("خطا در آپدیت پیام اعضا: %s", e)
    else:
        await query.edit_message_text(
            f"قبلاً توی کتاب «{book['title']}» ثبت‌نام کرده بودی."
        )
    return ConversationHandler.END


async def my_books_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    user_row = db.get_user_by_telegram_id(update.effective_user.id)
    books = db.get_user_books(user_row["id"]) if user_row else []
    if not books:
        return await end_and_show_menu(
            update, context, "هنوز توی هیچ کتابی ثبت‌نام نکردی."
        )
    lines = ["📖 کتاب‌های تو:\n"]
    for b in books:
        lines.append(f"- {b['title']} ({STATUS_LABELS.get(b['status'], b['status'])})")
    return await end_and_show_menu(update, context, "\n".join(lines))


ENTRY_POINTS = [
    MessageHandler(button_filter(BTN_ACTIVE_BOOKS), registration_start),
    MessageHandler(button_filter(BTN_MY_BOOKS), my_books_handler),
]

STATES = {
    S.REG_CHOOSE_BOOK: [CallbackQueryHandler(registration_choose, pattern="^reg:")],
}