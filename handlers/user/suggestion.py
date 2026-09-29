# -*- coding: utf-8 -*-
"""
پیشنهاد کتاب برای نظرسنجی انتخاب کتاب (گروه «تحلیل کتاب»).

فقط وقتی یک نظرسنجی «باز» وجود داشته باشد کاربر می‌تواند پیشنهاد بدهد.
هر کاربر فقط یک پیشنهاد فعال در هر نظرسنجی دارد؛ اگر دوباره پیشنهاد بدهد،
پیشنهاد قبلی‌اش جایگزین می‌شود (تا وقتی نظرسنجی باز است).
"""
from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
)

import database as db
from utils.keyboards import CANCEL_KB, BTN_SUGGEST_BOOK
from handlers.common import TEXT_INPUT, end_and_show_menu, button_filter
from handlers.states import S
from handlers.admin.poll import refresh_group_poll_message


async def suggest_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    poll = db.get_open_poll()
    if not poll:
        return await end_and_show_menu(
            update, context, "در حال حاضر نظرسنجی باز کتابی وجود نداره."
        )

    tg_user = update.effective_user
    db.upsert_user(tg_user.id, tg_user.username, tg_user.full_name)
    user_row = db.get_user_by_telegram_id(tg_user.id)

    context.user_data["suggest_poll_id"] = poll["id"]

    existing = db.get_user_suggestion(poll["id"], user_row["id"])
    if existing:
        author_part = f" - ✍️ {existing['author']}" if existing["author"] else ""
        await update.message.reply_text(
            "قبلاً برای این نظرسنجی این کتاب رو پیشنهاد داده بودی:\n"
            f"📖 {existing['book_title']}{author_part}\n\n"
            "اگه می‌خوای عوضش کنی، اسم کتاب جدید رو بفرست (یا /cancel بزن تا بی‌خیال بشی):",
            reply_markup=CANCEL_KB,
        )
    else:
        await update.message.reply_text(
            "اسم کتابی که پیشنهاد می‌دی رو بفرست:", reply_markup=CANCEL_KB
        )
    return S.SUGGEST_TITLE


async def suggest_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    title = update.message.text.strip()
    if not title:
        await update.message.reply_text("اسم کتاب نمی‌تونه خالی باشه، دوباره بفرست:")
        return S.SUGGEST_TITLE

    context.user_data["suggest_title"] = title
    await update.message.reply_text(
        "اسم نویسنده رو بفرست (اگه نمی‌دونی یا نداره، - بفرست):"
    )
    return S.SUGGEST_AUTHOR


async def suggest_author(update: Update, context: ContextTypes.DEFAULT_TYPE):
    poll_id = context.user_data.get("suggest_poll_id")
    title = context.user_data.get("suggest_title")

    if not poll_id or not title:
        return await end_and_show_menu(
            update, context, "مشکلی پیش اومد، دوباره از منو شروع کن."
        )

    poll = db.get_poll(poll_id)
    if not poll or poll["status"] != "open":
        context.user_data.clear()
        return await end_and_show_menu(
            update, context, "این نظرسنجی بسته شده، پیشنهادت ثبت نشد."
        )

    raw_author = update.message.text.strip()
    author = "" if raw_author == "-" else raw_author

    tg_user = update.effective_user
    user_row = db.get_user_by_telegram_id(tg_user.id)
    if not user_row:
        return await end_and_show_menu(
            update, context, "مشکلی پیش اومد، دوباره از منو شروع کن."
        )

    is_new = db.add_book_suggestion(poll_id, user_row["id"], title, author)

    # پیام زنده‌ی لیست پیشنهادها را در گروه «تحلیل کتاب» به‌روزرسانی کن
    await refresh_group_poll_message(context, db.get_poll(poll_id))

    context.user_data.clear()
    author_part = f" - ✍️ {author}" if author else ""
    verb = "ثبت شد" if is_new else "به‌روزرسانی شد"
    return await end_and_show_menu(
        update,
        context,
        f"✅ پیشنهادت {verb}:\n📖 {title}{author_part}",
    )


ENTRY_POINTS = [MessageHandler(button_filter(BTN_SUGGEST_BOOK), suggest_start)]

STATES = {
    S.SUGGEST_TITLE: [MessageHandler(TEXT_INPUT, suggest_title)],
    S.SUGGEST_AUTHOR: [MessageHandler(TEXT_INPUT, suggest_author)],
}
