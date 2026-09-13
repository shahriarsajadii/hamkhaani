# -*- coding: utf-8 -*-
"""
لیست اعضای همخوانی و تعداد روزهای خوانده‌شده.
هم ادمین هم کاربر عادی می‌توانند این را ببینند.
"""
from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
)

import database as db
from utils.keyboards import books_kb, BTN_MEMBERS_LIST
from handlers.common import end_and_show_menu, button_filter
from handlers.states import S


async def members_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    # همه کتاب‌های فعال را نشان می‌دهیم
    books = db.list_books(status="active")
    if not books:
        return await end_and_show_menu(update, context, "در حال حاضر کتاب فعالی وجود ندارد.")
    await update.message.reply_text(
        "لیست اعضای کدوم کتاب رو می‌خوای ببینی؟",
        reply_markup=books_kb(books, "members_book"),
    )
    return S.MEMBERS_CHOOSE_BOOK


async def members_choose_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    book_id = int(query.data.split(":")[1])
    book = db.get_book(book_id)
    if not book:
        await query.edit_message_text("کتاب پیدا نشد.")
        return ConversationHandler.END

    members = db.get_book_members_progress(book_id)
    total_days = len(db.get_reading_days(book_id))

    if not members:
        await query.edit_message_text(
            f"📖 «{book['title']}»\n\nهنوز کسی در این همخوانی ثبت‌نام نکرده."
        )
        return ConversationHandler.END

    lines = [f"📖 «{book['title']}»", f"👥 تعداد اعضا: {len(members)}", ""]
    for i, m in enumerate(members, start=1):
        name = m["full_name"] or "کاربر"
        username = f"@{m['username']}" if m["username"] else f"ID:{m['telegram_id']}"
        read = m["read_days"]
        if total_days > 0:
            lines.append(f"👤 {name} {username}\n" f" 📖 {read} از {total_days} روز")
        else:
            lines.append(f"👤 {name} {username}\n" f" 📖 {read} روز")
    await query.edit_message_text("\n".join(lines))
    return ConversationHandler.END


ENTRY_POINTS = [
    MessageHandler(button_filter(BTN_MEMBERS_LIST), members_start),
]

STATES = {
    S.MEMBERS_CHOOSE_BOOK: [
        CallbackQueryHandler(members_choose_book, pattern="^members_book:"),
    ],
}