# -*- coding: utf-8 -*-
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

# ------------------------------------------------------------ منوهای اصلی --

BTN_NEW_BOOK = "➕ کتاب جدید"
BTN_SCHEDULE = "📅 تعیین برنامه همخوانی"
BTN_QUESTIONS = "❓ تعیین سوالات کتاب"
BTN_DAY_REPORT = "📊 گزارش روز"
BTN_QUESTION_REPORT = "📋 گزارش سوالات"
BTN_LIST_BOOKS = "📚 لیست کتاب‌ها"
BTN_EDIT_BOOK = "✏️ ویرایش کتاب"
BTN_DELETE_BOOK = "🗑 حذف کتاب"
BTN_ACTIVATE_BOOK = "🚀 فعال‌سازی کتاب"

BTN_ACTIVE_BOOKS = "📚 کتاب‌های فعال"
BTN_MY_BOOKS = "📖 کتاب‌های من"
BTN_TODAY_REPORT = "✅ گزارش امروز"
BTN_ANSWER_QUESTIONS = "📝 پاسخ به سوالات"

ADMIN_BUTTONS = [
    BTN_NEW_BOOK, BTN_SCHEDULE, BTN_QUESTIONS, BTN_DAY_REPORT,
    BTN_QUESTION_REPORT, BTN_LIST_BOOKS, BTN_EDIT_BOOK, BTN_DELETE_BOOK,
    BTN_ACTIVATE_BOOK,
]

USER_BUTTONS = [
    BTN_ACTIVE_BOOKS, BTN_MY_BOOKS, BTN_TODAY_REPORT, BTN_ANSWER_QUESTIONS,
]

ALL_MENU_BUTTONS = ADMIN_BUTTONS + USER_BUTTONS

ADMIN_MENU = ReplyKeyboardMarkup(
    [
        [BTN_NEW_BOOK, BTN_SCHEDULE],
        [BTN_QUESTIONS, BTN_DAY_REPORT],
        [BTN_QUESTION_REPORT, BTN_LIST_BOOKS],
        [BTN_EDIT_BOOK, BTN_DELETE_BOOK],
        [BTN_ACTIVATE_BOOK],
    ],
    resize_keyboard=True,
)

USER_MENU = ReplyKeyboardMarkup(
    [
        [BTN_ACTIVE_BOOKS, BTN_MY_BOOKS],
        [BTN_TODAY_REPORT, BTN_ANSWER_QUESTIONS],
    ],
    resize_keyboard=True,
)

CANCEL_KB = ReplyKeyboardMarkup([["/cancel"]], resize_keyboard=True)


def yes_no_kb(prefix: str, ref_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ بله خوندم", callback_data=f"{prefix}:yes:{ref_id}"),
                InlineKeyboardButton("❌ نه هنوز", callback_data=f"{prefix}:no:{ref_id}"),
            ]
        ]
    )


def books_kb(books, prefix: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(b["title"], callback_data=f"{prefix}:{b['id']}")]
        for b in books
    ]
    return InlineKeyboardMarkup(rows)


def fields_kb(fields, prefix: str) -> InlineKeyboardMarkup:
    """fields لیستی از (key, label) است."""
    rows = [
        [InlineKeyboardButton(label, callback_data=f"{prefix}:{key}")]
        for key, label in fields
    ]
    return InlineKeyboardMarkup(rows)


def reading_days_kb(days, prefix: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(f"روز {d['day_index']} - {d['jalali_date']}",
                               callback_data=f"{prefix}:{d['id']}")]
        for d in days
    ]
    return InlineKeyboardMarkup(rows)


def questions_kb(questions, prefix: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(f"سوال {q['order_index']}", callback_data=f"{prefix}:{q['id']}")]
        for q in questions
    ]
    return InlineKeyboardMarkup(rows)


def confirm_kb(prefix: str, ref_id) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ تأیید و ثبت", callback_data=f"{prefix}:confirm:{ref_id}"),
                InlineKeyboardButton("❌ انصراف", callback_data=f"{prefix}:cancel:{ref_id}"),
            ]
        ]
    )
