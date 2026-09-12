# -*- coding: utf-8 -*-
"""
مراحل ادمین برای:
  1) ساخت کتاب جدید (عنوان، نویسنده، توضیحات)
  2) اتصال تاپیک‌ها: ادمین باید داخل گروه، در هر کدوم از سه تاپیک
     دستور /settopic <book_id> <pigiri|boride|gap> را بفرستد.
  3) فعال‌سازی کتاب (بعد از تعیین برنامه): اعلان رسمی در تاپیک «گپ» پست می‌شود.
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
from utils.keyboards import ADMIN_MENU, CANCEL_KB, books_kb
from utils.formatting import format_schedule_announcement
from utils.jalali import parse_jalali, format_jalali_human
from handlers.common import is_admin

TITLE, AUTHOR, DESCRIPTION = range(3)
CHOOSE_BOOK_TO_ACTIVATE = 100


# ------------------------------------------------------------- ساخت کتاب --

async def new_book_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END
    await update.message.reply_text(
        "عنوان کتاب رو بفرست (مثال: آدمخواران):", reply_markup=CANCEL_KB
    )
    return TITLE


async def new_book_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_book_title"] = update.message.text.strip()
    await update.message.reply_text("اسم نویسنده رو بفرست:")
    return AUTHOR


async def new_book_author(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_book_author"] = update.message.text.strip()
    await update.message.reply_text("یه توضیح کوتاه درباره کتاب بنویس (یا - بفرست اگه نمی‌خوای):")
    return DESCRIPTION


async def new_book_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    desc = update.message.text.strip()
    if desc == "-":
        desc = ""
    title = context.user_data.pop("new_book_title")
    author = context.user_data.pop("new_book_author")

    book_id = db.create_book(title, author, desc)

    await update.message.reply_text(
        f"✅ کتاب «{title}» با شناسه #{book_id} ساخته شد.\n\n"
        "حالا برای اتصال تاپیک‌های این کتاب:\n"
        "۱) وارد گروه شو.\n"
        "۲) داخل هر کدوم از سه تاپیک (پیگیری، بریده‌ها، گپ)، این دستور رو بفرست:\n\n"
        f"در تاپیک «پیگیری» بفرست:\n<code>/settopic {book_id} pigiri</code>\n\n"
        f"در تاپیک «بریده‌ها» بفرست:\n<code>/settopic {book_id} boride</code>\n\n"
        f"در تاپیک «گپ» بفرست:\n<code>/settopic {book_id} gap</code>\n\n"
        "بعدش می‌تونی از منو، «📅 تعیین برنامه همخوانی» رو بزنی.",
        parse_mode="HTML",
        reply_markup=ADMIN_MENU,
    )
    return ConversationHandler.END


book_conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^➕ کتاب جدید$"), new_book_start)],
    states={
        TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_book_title)],
        AUTHOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_book_author)],
        DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_book_description)],
    },
    fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
)


# ---------------------------------------------------------- اتصال تاپیک‌ها --

async def set_topic_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    msg = update.message
    if msg.chat.type not in ("group", "supergroup"):
        await msg.reply_text("این دستور فقط باید داخل گروه و در تاپیک موردنظر فرستاده بشه.")
        return

    args = context.args
    if len(args) != 2 or args[1] not in ("pigiri", "boride", "gap"):
        await msg.reply_text("فرمت درست: /settopic <book_id> <pigiri|boride|gap>")
        return

    try:
        book_id = int(args[0])
    except ValueError:
        await msg.reply_text("شناسه کتاب باید عدد باشه.")
        return

    book = db.get_book(book_id)
    if not book:
        await msg.reply_text("کتابی با این شناسه پیدا نشد.")
        return

    thread_id = msg.message_thread_id  # ممکنه None باشه اگه گروه توپیک نداشته باشه
    db.set_book_topic(book_id, args[1], msg.chat_id, thread_id)

    labels = {"pigiri": "پیگیری", "boride": "بریده‌ها", "gap": "گپ"}
    await msg.reply_text(f"✅ تاپیک «{labels[args[1]]}» برای کتاب «{book['title']}» ثبت شد.")


# --------------------------------------------------------- فعال‌سازی کتاب --

async def activate_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END
    drafts = db.list_books(status="draft")
    if not drafts:
        await update.message.reply_text("کتاب آماده‌ای برای فعال‌سازی وجود نداره.")
        return ConversationHandler.END
    await update.message.reply_text(
        "کدوم کتاب رو فعال کنم؟ (اعلان رسمی برنامه توی تاپیک «گپ» پست می‌شه)",
        reply_markup=books_kb(drafts, "activate"),
    )
    return CHOOSE_BOOK_TO_ACTIVATE


async def activate_choose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    book_id = int(query.data.split(":")[1])
    book = db.get_book(book_id)

    if not book["group_chat_id"] or not book["topic_gap_id"]:
        await query.edit_message_text(
            "⚠️ اول باید تاپیک‌های این کتاب رو با /settopic ثبت کنی."
        )
        return ConversationHandler.END

    days = db.get_reading_days(book_id)
    if not days:
        await query.edit_message_text("⚠️ اول باید برنامه روزهای همخوانی رو تعیین کنی.")
        return ConversationHandler.END

    days_for_format = []
    for d in days:
        jd = parse_jalali(d["jalali_date"])
        days_for_format.append({**dict(d), "jalali_date_human": format_jalali_human(jd)})

    text = format_schedule_announcement(book, days_for_format)

    await context.bot.send_message(
        chat_id=book["group_chat_id"],
        message_thread_id=book["topic_gap_id"],
        text=text,
    )
    db.set_book_status(book_id, "active")
    await query.edit_message_text(f"✅ کتاب «{book['title']}» فعال شد و اعلان در تاپیک گپ پست شد.")
    return ConversationHandler.END


activate_book_conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^🚀 فعال‌سازی کتاب$"), activate_start)],
    states={
        CHOOSE_BOOK_TO_ACTIVATE: [
            CallbackQueryHandler(activate_choose, pattern="^activate:")
        ],
    },
    fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
)
