# -*- coding: utf-8 -*-
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

# ------------------------------------------------------------ منوهای اصلی --

ADMIN_MENU = ReplyKeyboardMarkup(
    [
        ["➕ کتاب جدید", "📅 تعیین برنامه همخوانی"],
        ["❓ تعیین سوالات کتاب", "📊 گزارش روز"],
        ["📋 گزارش سوالات", "📚 لیست کتاب‌ها"],
        ["🚀 فعال‌سازی کتاب"],
    ],
    resize_keyboard=True,
)

USER_MENU = ReplyKeyboardMarkup(
    [
        ["📚 کتاب‌های فعال", "📖 کتاب‌های من"],
        ["✅ گزارش امروز", "📝 پاسخ به سوالات"],
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
