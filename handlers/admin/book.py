# -*- coding: utf-8 -*-
"""
مسیرهای ادمین برای کتاب - نسخه اصلاح‌شده:

تغییرات:
- اضافه شدن «غیرفعال‌سازی کتاب» (active -> draft)
- دکمه‌های برگشت در مراحل چندگانه
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
)

import database as db
from utils.keyboards import (
    ADMIN_MENU,
    CANCEL_KB,
    books_kb,
    books_with_status_kb,
    fields_kb,
    BTN_NEW_BOOK,
    BTN_EDIT_BOOK,
    BTN_DELETE_BOOK,
    BTN_ACTIVATE_BOOK,
    BTN_DEACTIVATE_BOOK,
)
from utils.formatting import format_schedule_announcement, format_book_info, format_members_list
from utils.jalali import days_with_human
from handlers.common import is_admin, TEXT_INPUT, end_and_show_menu, button_filter
from handlers.states import S

EDITABLE_FIELDS = [
    ("title", "📖 عنوان"),
    ("author", "✍️ نویسنده"),
    ("description", "📝 توضیحات"),
    ("book_pages", "📄 تعداد صفحات کتاب"),
    ("pdf_pages", "💻 تعداد صفحات پی‌دی‌اف"),
]
FIELD_LABELS = dict(EDITABLE_FIELDS)
NUMERIC_FIELDS = {"book_pages", "pdf_pages"}


def _parse_pages(text: str) -> int:
    value = int(text.strip())
    if value < 1:
        raise ValueError
    return value


def _back_to_fields_kb(book_id: int) -> InlineKeyboardMarkup:
    """کیبورد برگشت به انتخاب فیلد ویرایش."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("↩️ برگشت به انتخاب فیلد", callback_data=f"edit_book:{book_id}")]
    ])


# ------------------------------------------------------------- ساخت کتاب --

async def new_book_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END
    context.user_data.clear()
    await update.message.reply_text(
        "عنوان کتاب رو بفرست (مثال: آدمخواران):", reply_markup=CANCEL_KB
    )
    return S.BOOK_TITLE


async def new_book_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_book_title"] = update.message.text.strip()
    await update.message.reply_text("اسم نویسنده رو بفرست:")
    return S.BOOK_AUTHOR


async def new_book_author(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_book_author"] = update.message.text.strip()
    await update.message.reply_text("یه توضیح کوتاه درباره کتاب بنویس (یا - بفرست اگه نمی‌خوای):")
    return S.BOOK_DESCRIPTION


async def new_book_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    desc = update.message.text.strip()
    context.user_data["new_book_description"] = "" if desc == "-" else desc
    await update.message.reply_text("تعداد کل صفحات کتاب چاپی رو بفرست (مثال: 320):")
    return S.BOOK_PAGES


async def new_book_pages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["new_book_pages"] = _parse_pages(update.message.text)
    except ValueError:
        await update.message.reply_text("باید یه عدد مثبت بفرستی، مثلا: 320")
        return S.BOOK_PAGES
    await update.message.reply_text("تعداد کل صفحات فایل پی‌دی‌اف رو بفرست (مثال: 180):")
    return S.BOOK_PDF_PAGES


async def new_book_pdf_pages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        pdf_pages = _parse_pages(update.message.text)
    except ValueError:
        await update.message.reply_text("باید یه عدد مثبت بفرستی، مثلا: 180")
        return S.BOOK_PDF_PAGES

    title = context.user_data.pop("new_book_title")
    author = context.user_data.pop("new_book_author")
    desc = context.user_data.pop("new_book_description")
    book_pages = context.user_data.pop("new_book_pages")

    book_id = db.create_book(title, author, desc, book_pages, pdf_pages)

    await update.message.reply_text(
        f"✅ کتاب «{title}» با شناسه #{book_id} ساخته شد.\n"
        f"📄 صفحات کتاب: {book_pages} | 💻 صفحات پی‌دی‌اف: {pdf_pages}\n\n"
        "حالا برای اتصال تاپیک «پیگیری» این کتاب:\n"
        "۱) وارد گروه شو و برو توی تاپیک «پیگیری».\n"
        f"۲) همونجا این دستور رو بفرست:\n<code>/settopic {book_id}</code>\n\n"
        "بعدش می‌تونی از منو، «📅 تعیین برنامه همخوانی» رو بزنی.",
        parse_mode="HTML",
        reply_markup=ADMIN_MENU,
    )
    return ConversationHandler.END


# ---------------------------------------------------------- اتصال تاپیک --

async def set_topic_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    msg = update.message
    if msg.chat.type not in ("group", "supergroup"):
        await msg.reply_text("این دستور فقط باید داخل گروه و در تاپیک «پیگیری» فرستاده بشه.")
        return

    args = context.args
    if not args:
        await msg.reply_text("فرمت درست: /settopic <book_id>")
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

    db.set_book_topic(book_id, msg.chat_id, msg.message_thread_id)

    # ارسال پیام اعضا در تاپیک و ذخیره شناسه آن برای آپدیت‌های آینده
    try:
        members = db.get_registered_users(book_id)
        members_text = format_members_list(book["title"], members)
        sent = await context.bot.send_message(
            chat_id=msg.chat_id,
            message_thread_id=msg.message_thread_id,
            text=members_text,
        )
        db.set_book_members_message_id(book_id, sent.message_id)
    except Exception:
        pass

    await msg.reply_text(f"✅ تاپیک «پیگیری» برای کتاب «{book['title']}» ثبت شد.")


# ----------------------------------------------------------- ویرایش کتاب --

async def edit_book_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END
    context.user_data.clear()
    books = db.list_books()
    if not books:
        return await end_and_show_menu(update, context, "هنوز کتابی ثبت نشده.")
    await update.message.reply_text(
        "کدوم کتاب رو ویرایش کنم؟", reply_markup=books_kb(books, "edit_book")
    )
    return S.EDIT_CHOOSE_BOOK


async def edit_book_choose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    book_id = int(query.data.split(":")[1])
    context.user_data["edit_book_id"] = book_id
    book = db.get_book(book_id)
    await query.edit_message_text(
        format_book_info(book) + "\n\nکدوم بخش رو عوض کنم؟",
        reply_markup=fields_kb(EDITABLE_FIELDS, "edit_field"),
    )
    return S.EDIT_CHOOSE_FIELD


async def edit_book_choose_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    field = query.data.split(":")[1]
    context.user_data["edit_field"] = field
    await query.edit_message_text(
        f"مقدار جدید برای «{FIELD_LABELS[field]}» رو بفرست:\n\n"
        "(برای انصراف /cancel بزن)"
    )
    return S.EDIT_VALUE


async def edit_book_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    field = context.user_data.get("edit_field")
    book_id = context.user_data.get("edit_book_id")
    if not field or not book_id:
        return await end_and_show_menu(update, context, "مشکلی پیش اومد، دوباره از منو شروع کن.")

    text = update.message.text.strip()
    if field in NUMERIC_FIELDS:
        try:
            value = _parse_pages(text)
        except ValueError:
            await update.message.reply_text("باید یه عدد مثبت بفرستی.")
            return S.EDIT_VALUE
    else:
        value = "" if text == "-" else text

    db.update_book_field(book_id, field, value)
    book = db.get_book(book_id)
    await update.message.reply_text(
        f"✅ «{FIELD_LABELS[field]}» به‌روز شد.\n\n" + format_book_info(book),
        reply_markup=fields_kb(EDITABLE_FIELDS, "edit_field"),
    )
    return S.EDIT_CHOOSE_FIELD


# -------------------------------------------------------------- حذف کتاب --

async def delete_book_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END
    context.user_data.clear()
    books = db.list_books()
    if not books:
        return await end_and_show_menu(update, context, "هنوز کتابی ثبت نشده.")
    await update.message.reply_text(
        "کدوم کتاب رو پاک کنم؟", reply_markup=books_kb(books, "del_book")
    )
    return S.DELETE_CHOOSE_BOOK


async def delete_book_choose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    book_id = int(query.data.split(":")[1])
    book = db.get_book(book_id)
    confirm_kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🗑 بله، پاک کن", callback_data=f"del_confirm:yes:{book_id}"),
                InlineKeyboardButton("↩️ انصراف", callback_data="del_confirm:no:0"),
            ]
        ]
    )
    await query.edit_message_text(
        f"⚠️ با حذف کتاب «{book['title']}» برنامه، ثبت‌نام‌ها، سوالات و پاسخ‌هاش هم پاک می‌شن.\n"
        "مطمئنی؟",
        reply_markup=confirm_kb,
    )
    return S.DELETE_CONFIRM


async def delete_book_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, answer, book_id = query.data.split(":")
    if answer != "yes":
        await query.edit_message_text("انصراف داده شد، چیزی پاک نشد.")
        return await end_and_show_menu(update, context, "برگشتیم به منو 👇")

    book = db.get_book(int(book_id))
    db.delete_book(int(book_id))
    await query.edit_message_text(f"🗑 کتاب «{book['title']}» پاک شد.")
    return await end_and_show_menu(update, context, "برگشتیم به منو 👇")


# --------------------------------------------------------- فعال‌سازی کتاب --

async def activate_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END
    context.user_data.clear()
    books = db.list_books()
    if not books:
        return await end_and_show_menu(update, context, "هنوز هیچ کتابی ثبت نشده.")

    status_labels = {
        "draft": "⏳ غیرفعال",
        "active": "✅ فعال",
        "finished": "🏁 پایان‌یافته",
    }
    await update.message.reply_text(
        "همهٔ کتاب‌ها و وضعیت آن‌ها:",
        reply_markup=books_with_status_kb(books, "activate", status_labels),
    )
    return S.ACTIVATE_CHOOSE_BOOK


async def activate_choose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    book_id = int(query.data.split(":")[1])
    book = db.get_book(book_id)
    if not book:
        await query.edit_message_text("این کتاب دیگر وجود ندارد.")
        return ConversationHandler.END

    if book["status"] == "active":
        await query.edit_message_text(f"✅ کتاب «{book['title']}» از قبل فعال است.")
        return ConversationHandler.END

    if book["status"] == "finished":
        await query.edit_message_text(f"🏁 کتاب «{book['title']}» پایان‌یافته است و قابل فعال‌سازی نیست.")
        return ConversationHandler.END

    if not book["group_chat_id"]:
        await query.edit_message_text(
            "⚠️ اول باید تاپیک «پیگیری» این کتاب رو با /settopic ثبت کنی."
        )
        return ConversationHandler.END

    days = db.get_reading_days(book_id)
    if not days:
        await query.edit_message_text("⚠️ اول باید برنامه روزهای همخوانی رو تعیین کنی.")
        return ConversationHandler.END

    text = format_schedule_announcement(book, days_with_human(days))

    await context.bot.send_message(
        chat_id=book["group_chat_id"],
        message_thread_id=book["topic_pigiri_id"],
        text=text,
    )
    db.set_book_status(book_id, "active")
    await query.edit_message_text(
        f"✅ کتاب «{book['title']}» فعال شد و اعلان در تاپیک پیگیری پست شد."
    )
    return ConversationHandler.END


# --------------------------------------------------------- غیرفعال‌سازی کتاب --

async def deactivate_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END
    context.user_data.clear()
    # فقط کتاب‌های فعال را نشان می‌دهیم
    books = db.list_books(status="active")
    if not books:
        return await end_and_show_menu(update, context, "هیچ کتاب فعالی برای غیرفعال‌سازی وجود ندارد.")
    await update.message.reply_text(
        "کدوم کتاب رو غیرفعال کنم؟",
        reply_markup=books_kb(books, "deactivate"),
    )
    return S.DEACTIVATE_CHOOSE_BOOK


async def deactivate_choose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    book_id = int(query.data.split(":")[1])
    book = db.get_book(book_id)
    if not book:
        await query.edit_message_text("این کتاب دیگر وجود ندارد.")
        return ConversationHandler.END

    if book["status"] != "active":
        await query.edit_message_text("این کتاب فعال نیست.")
        return ConversationHandler.END

    confirm_kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⏸ بله، غیرفعال کن", callback_data=f"deact_confirm:yes:{book_id}"),
            InlineKeyboardButton("↩️ انصراف", callback_data="deact_confirm:no:0"),
        ]
    ])
    await query.edit_message_text(
        f"⚠️ مطمئنی می‌خوای کتاب «{book['title']}» رو غیرفعال کنی؟\n"
        "ثبت‌نام‌ها و گزارش‌ها حفظ می‌شوند ولی کاربران دیگر نمی‌توانند گزارش جدید بدهند.",
        reply_markup=confirm_kb,
    )
    return S.DEACTIVATE_CONFIRM


async def deactivate_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, answer, book_id = query.data.split(":")
    if answer != "yes":
        await query.edit_message_text("انصراف داده شد.")
        return await end_and_show_menu(update, context, "برگشتیم به منو 👇")

    book = db.get_book(int(book_id))
    db.set_book_status(int(book_id), "draft")
    await query.edit_message_text(f"⏸ کتاب «{book['title']}» غیرفعال شد.")
    return await end_and_show_menu(update, context, "برگشتیم به منو 👇")


ENTRY_POINTS = [
    MessageHandler(button_filter(BTN_NEW_BOOK), new_book_start),
    MessageHandler(button_filter(BTN_EDIT_BOOK), edit_book_start),
    MessageHandler(button_filter(BTN_DELETE_BOOK), delete_book_start),
    MessageHandler(button_filter(BTN_ACTIVATE_BOOK), activate_start),
    MessageHandler(button_filter(BTN_DEACTIVATE_BOOK), deactivate_start),
]

STATES = {
    S.BOOK_TITLE: [MessageHandler(TEXT_INPUT, new_book_title)],
    S.BOOK_AUTHOR: [MessageHandler(TEXT_INPUT, new_book_author)],
    S.BOOK_DESCRIPTION: [MessageHandler(TEXT_INPUT, new_book_description)],
    S.BOOK_PAGES: [MessageHandler(TEXT_INPUT, new_book_pages)],
    S.BOOK_PDF_PAGES: [MessageHandler(TEXT_INPUT, new_book_pdf_pages)],
    S.EDIT_CHOOSE_BOOK: [CallbackQueryHandler(edit_book_choose, pattern="^edit_book:")],
    S.EDIT_CHOOSE_FIELD: [CallbackQueryHandler(edit_book_choose_field, pattern="^edit_field:")],
    S.EDIT_VALUE: [MessageHandler(TEXT_INPUT, edit_book_value)],
    S.DELETE_CHOOSE_BOOK: [CallbackQueryHandler(delete_book_choose, pattern="^del_book:")],
    S.DELETE_CONFIRM: [CallbackQueryHandler(delete_book_confirm, pattern="^del_confirm:")],
    S.ACTIVATE_CHOOSE_BOOK: [CallbackQueryHandler(activate_choose, pattern="^activate:")],
    S.DEACTIVATE_CHOOSE_BOOK: [CallbackQueryHandler(deactivate_choose, pattern="^deactivate:")],
    S.DEACTIVATE_CONFIRM: [CallbackQueryHandler(deactivate_confirm, pattern="^deact_confirm:")],
}