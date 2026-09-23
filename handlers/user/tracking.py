# -*- coding: utf-8 -*-
"""
گزارش مطالعه کاربر:

- کاربر نمی‌تواند روز N را گزارش دهد مگر آنکه روز N-1 را قبلاً گزارش داده باشد.
- وقتی کاربر آخرین روز کتاب را گزارش می‌دهد، پیام «کتاب را تمام کردی» در گروه ارسال می‌شود.
"""

import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
)

import database as db
from utils.keyboards import (
    reading_days_kb,
    BTN_TODAY_REPORT,
    BTN_MY_REPORTS,
    books_kb,
)
from utils.jalali import parse_jalali, format_jalali_human
from utils.formatting import format_daily_report_line
from handlers.common import end_and_show_menu, button_filter
from handlers.states import S


STATUS_LABELS = {
    "pending": "⏳ گزارش نشده",
    "read": "✅ خواندم",
}


def _today_gregorian() -> str:
    return str(datetime.date.today())


def _user_identifier(user_row) -> str:
    if user_row["username"]:
        return f"@{user_row['username']}"
    return f"ID:{user_row['telegram_id']}"


def _day_status_by_id(progress_rows):
    return {
        row["reading_day_id"]: STATUS_LABELS.get(row["status"], "⏳ گزارش نشده")
        for row in progress_rows
    }


def _report_days_text(book, progress_rows) -> str:
    lines = [f"📖 گزارش کتاب «{book['title']}»", ""]

    if not progress_rows:
        lines.append("هنوز هیچ گزارشی برای این کتاب ثبت نشده.")
        return "\n".join(lines)

    for row in progress_rows:
        jd = parse_jalali(row["jalali_date"])
        status = "✅ خواندم" if row["status"] == "read" else "⏳ گزارش نشده"
        lines.append(
            f"روز {row['day_index']} - {format_jalali_human(jd)}: {status}"
        )

    return "\n".join(lines)


def _read_confirm_kb(reading_day_id: int, book_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ خوندم",
                    callback_data=f"track:{reading_day_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    "↩️ برگشت به لیست روزها",
                    callback_data=f"report_book:{book_id}",
                )
            ],
        ]
    )


# ------------------------------------------------------- ثبت گزارش مطالعه --


async def report_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    user_row = db.get_user_by_telegram_id(update.effective_user.id)

    if not user_row:
        return await end_and_show_menu(
            update, context, "اول باید توی یه کتاب ثبت‌نام کنی."
        )

    books = db.get_user_books(user_row["id"], status="active")

    if not books:
        return await end_and_show_menu(
            update, context, "توی هیچ کتاب فعالی ثبت‌نام نکردی."
        )

    await update.message.reply_text(
        "گزارش کدوم کتاب رو ثبت کنم؟",
        reply_markup=books_kb(books, "report_book"),
    )

    return S.REPORT_CHOOSE_BOOK


async def report_choose_book(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    await query.answer()

    book_id = int(query.data.split(":")[1])

    book = db.get_book(book_id)
    user_row = db.get_user_by_telegram_id(update.effective_user.id)

    if not book or not user_row:
        await query.edit_message_text("کتاب یا کاربر پیدا نشد.")
        return ConversationHandler.END

    if book["status"] != "active":
        await query.edit_message_text(
            "گزارش دادن فقط برای کتاب فعال امکان‌پذیر است."
        )
        return ConversationHandler.END

    if not db.is_user_registered(book_id, user_row["id"]):
        await query.edit_message_text("توی این کتاب ثبت‌نام نکردی.")
        return ConversationHandler.END

    days = db.get_reading_days(book_id)

    if not days:
        await query.edit_message_text("این کتاب هنوز برنامهٔ خواندن ندارد.")
        return ConversationHandler.END

    progress = db.get_user_book_progress(user_row["id"], book_id)
    context.user_data["report_book_id"] = book_id
    status_by_day = _day_status_by_id(progress)

    await query.edit_message_text(
        _report_days_text(book, progress) + "\n\nروز موردنظر را انتخاب کن:",
        reply_markup=reading_days_kb(days, "report_day", status_by_day),
    )

    return S.REPORT_CHOOSE_DAY


async def report_choose_day(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    await query.answer()

    reading_day_id = int(query.data.split(":")[1])
    book_id = context.user_data.get("report_book_id")
    user_row = db.get_user_by_telegram_id(update.effective_user.id)
    rday = db.get_reading_day(reading_day_id)

    if not book_id or not user_row or not rday:
        await query.edit_message_text("اطلاعات گزارش پیدا نشد.")
        return ConversationHandler.END

    book = db.get_book(rday["book_id"])

    if rday["book_id"] != book_id or not book:
        await query.edit_message_text("روز انتخاب‌شده مربوط به این کتاب نیست.")
        return ConversationHandler.END

    if book["status"] != "active":
        await query.edit_message_text(
            "گزارش دادن فقط برای کتاب فعال امکان‌پذیر است."
        )
        return ConversationHandler.END

    if not db.is_user_registered(book_id, user_row["id"]):
        await query.edit_message_text("توی این کتاب ثبت‌نام نکردی.")
        return ConversationHandler.END

    # بررسی ترتیب: کاربر نمی‌تواند روز N را بدون گزارش روز N-1 ثبت کند
    current_day_index = rday["day_index"]
    if not db.is_previous_day_reported(book_id, user_row["id"], current_day_index):
        prev_index = current_day_index - 1
        await query.edit_message_text(
            f"⚠️ برای ثبت گزارش روز {current_day_index}، ابتدا باید گزارش روز {prev_index} را ثبت کنی.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("↩️ برگشت به لیست روزها", callback_data=f"report_book:{book_id}")
            ]])
        )
        return S.REPORT_CHOOSE_DAY

    existing = db.get_progress_for_user(reading_day_id, user_row["id"])

    if existing and existing["status"] == "read":
        await query.edit_message_text(
            "✅ این روز قبلاً به عنوان «خواندم» ثبت شده و دیگر قابل تغییر نیست.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("↩️ برگشت به لیست روزها", callback_data=f"report_book:{book_id}")
            ]])
        )
        return S.REPORT_CHOOSE_DAY

    jd = parse_jalali(rday["jalali_date"])

    pdf_line = ""
    if rday["pdf_page_from"] and rday["pdf_page_to"]:
        pdf_line = f"\n💻 پی‌دی‌اف {rday['pdf_page_from']} تا {rday['pdf_page_to']}"

    await query.edit_message_text(
        f"📖 «{book['title']}»\n"
        f"🗓 {format_jalali_human(jd)}\n"
        f"📚 صفحه {rday['book_page_from']} تا {rday['book_page_to']}"
        f"{pdf_line}\n\n"
        "این بخش رو خوندی؟",
        reply_markup=_read_confirm_kb(reading_day_id, book_id),
    )

    return S.REPORT_CHOOSE_DAY


# ----------------------------------------------------------- گزارش‌های من --


async def my_reports_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data.clear()

    user_row = db.get_user_by_telegram_id(update.effective_user.id)

    if not user_row:
        return await end_and_show_menu(
            update, context, "اول باید توی یه کتاب ثبت‌نام کنی."
        )

    books = db.get_user_books(user_row["id"])

    if not books:
        return await end_and_show_menu(
            update, context, "هنوز توی هیچ کتابی ثبت‌نام نکردی."
        )

    await update.message.reply_text(
        "گزارش کدوم کتاب رو می‌خوای ببینی؟",
        reply_markup=books_kb(books, "myrep_book"),
    )

    return S.MYREPORT_CHOOSE_BOOK


async def my_reports_choose_book(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    await query.answer()

    book_id = int(query.data.split(":")[1])
    user_row = db.get_user_by_telegram_id(update.effective_user.id)
    book = db.get_book(book_id)

    if not user_row or not book:
        await query.edit_message_text("کتاب یا کاربر پیدا نشد.")
        return ConversationHandler.END

    if not db.is_user_registered(book_id, user_row["id"]):
        await query.edit_message_text("توی این کتاب ثبت‌نام نکردی.")
        return ConversationHandler.END

    progress = db.get_user_book_progress(user_row["id"], book_id)

    await query.edit_message_text(_report_days_text(book, progress))

    return ConversationHandler.END


# ----------------------------------------------------------- callback ثبت خواندن --


async def tracking_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """ثبت گزارش «خواندم» از طریق دکمه inline.

    دو فرمت callback_data پشتیبانی می‌شود:
      - track:<reading_day_id>           ← از منوی ربات (پیوی)
      - track:yes:<reading_day_id>       ← از یادآوری روزانه (پیوی یا گروه)
      - track:no:<reading_day_id>        ← دکمه «نه هنوز» — فقط تأیید می‌گیریم
    """

    query = update.callback_query
    await query.answer()

    try:
        parts = query.data.split(":")
        if len(parts) == 3:
            # فرمت: track:yes:ID یا track:no:ID
            action = parts[1]
            reading_day_id = int(parts[2])
            if action == "no":
                await query.edit_message_text("باشه! فراموش نکنی بعداً ثبتش کنی 📖")
                return
        else:
            # فرمت: track:ID
            reading_day_id = int(parts[1])
    except (ValueError, IndexError, AttributeError):
        await query.edit_message_text("داده گزارش نامعتبر است.")
        return

    tg_user = update.effective_user
    user_row = db.get_user_by_telegram_id(tg_user.id)

    async def _reply(text: str):
        """ویرایش پیام اصلی یا ارسال پیام جدید (در گروه‌ها edit ممکن است نشود)."""
        try:
            await query.edit_message_text(text)
        except Exception:
            try:
                await query.message.reply_text(text)
            except Exception:
                pass

    if not user_row:
        await _reply("خطا: کاربر پیدا نشد.")
        return

    rday = db.get_reading_day(reading_day_id)

    if not rday:
        await _reply("این روز دیگر وجود ندارد.")
        return

    book = db.get_book(rday["book_id"])

    if not book:
        await _reply("کتاب پیدا نشد.")
        return

    if book["status"] != "active":
        await _reply("گزارش دادن فقط برای کتاب فعال امکان‌پذیر است.")
        return

    if not db.is_user_registered(book["id"], user_row["id"]):
        await _reply("شما در این کتاب ثبت‌نام نکرده‌اید.")
        return

    # بررسی ترتیب روزها از یادآور روزانه
    current_day_index = rday["day_index"]
    if not db.is_previous_day_reported(book["id"], user_row["id"], current_day_index):
        prev_index = current_day_index - 1
        await _reply(
            f"⚠️ برای ثبت گزارش روز {current_day_index}، ابتدا باید گزارش روز {prev_index} را ثبت کنی.\n"
            "از ربات (ثبت گزارش مطالعه) اقدام کن."
        )
        return

    # بررسی اینکه قبلاً «خواندم» ثبت شده باشد
    existing = db.get_progress_for_user(reading_day_id, user_row["id"])

    if existing and existing["status"] == "read":
        await _reply("✅ این روز قبلاً به عنوان «خواندم» ثبت شده و دیگر قابل تغییر نیست.")
        return

    # ثبت گزارش خواندن
    created = db.set_progress(reading_day_id, user_row["id"], "read")

    jd = parse_jalali(rday["jalali_date"])
    human_date = format_jalali_human(jd)

    if not created:
        existing = db.get_progress_for_user(reading_day_id, user_row["id"])
        if existing and existing["status"] == "read":
            await _reply("✅ این روز قبلاً به عنوان «خواندم» ثبت شده و دیگر قابل تغییر نیست.")
        else:
            await _reply("⚠️ مشکلی در ثبت گزارش پیش اومد. دوباره امتحان کن.")
        return

    await _reply("✅ گزارش ثبت شد: این بخش رو خوندم 📖")

    # اعلام در تاپیک «پیگیری» گروه
    if book["group_chat_id"]:
        full_name = user_row["full_name"] or "کاربر"
        line = format_daily_report_line(
            full_name,
            _user_identifier(user_row),
            human_date,
            True,
        )
        try:
            await context.bot.send_message(
                chat_id=book["group_chat_id"],
                message_thread_id=book["topic_pigiri_id"],
                text=line,
            )
        except Exception:
            pass

        # بررسی اینکه آیا کاربر همه روزها را تمام کرد
        all_days = db.get_reading_days(book["id"])
        total_days = len(all_days)
        if total_days > 0 and rday["day_index"] == total_days:
            # آخرین روز کتاب — بررسی که واقعاً همه روزها «خوانده» شده‌اند
            progress = db.get_user_book_progress(user_row["id"], book["id"])
            all_read = all(row["status"] == "read" for row in progress)
            if all_read:
                try:
                    await context.bot.send_message(
                        chat_id=book["group_chat_id"],
                        message_thread_id=book["topic_pigiri_id"],
                        text=(
                            f"🎉 {full_name} | {_user_identifier(user_row)} "
                            f"کتاب «{book['title']}» رو به پایان رساند! 🏁📖\n"
                            "آفرین، مبارک باشه! 🌟"
                        ),
                    )
                except Exception:
                    pass


tracking_callback_handler = CallbackQueryHandler(
    tracking_callback,
    pattern=r"^track:(yes:|no:)?\d+$",
)


ENTRY_POINTS = [
    MessageHandler(button_filter(BTN_TODAY_REPORT), report_start),
    MessageHandler(button_filter(BTN_MY_REPORTS), my_reports_start),
]


STATES = {
    S.REPORT_CHOOSE_BOOK: [
        CallbackQueryHandler(report_choose_book, pattern="^report_book:"),
    ],
    S.REPORT_CHOOSE_DAY: [
        CallbackQueryHandler(report_choose_day, pattern="^report_day:"),
        # برگشت از صفحه تأیید به لیست روزها
        CallbackQueryHandler(report_choose_book, pattern="^report_book:"),
    ],
    S.MYREPORT_CHOOSE_BOOK: [
        CallbackQueryHandler(my_reports_choose_book, pattern="^myrep_book:"),
    ],
}