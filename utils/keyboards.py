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
BTN_DEACTIVATE_BOOK = "⏸ غیرفعال‌سازی کتاب"

BTN_ACTIVE_BOOKS = "📚 کتاب‌های فعال"
BTN_MY_BOOKS = "📖 کتاب‌های من"
BTN_TODAY_REPORT = "✅ ثبت گزارش مطالعه"
BTN_MY_REPORTS = "📊 گزارش‌های من"
BTN_ANSWER_QUESTIONS = "📝 پاسخ به سوالات"
BTN_MEMBERS_LIST = "👥 لیست اعضا"

ADMIN_BUTTONS = [
    BTN_NEW_BOOK,
    BTN_SCHEDULE,
    BTN_QUESTIONS,
    BTN_DAY_REPORT,
    BTN_QUESTION_REPORT,
    BTN_LIST_BOOKS,
    BTN_EDIT_BOOK,
    BTN_DELETE_BOOK,
    BTN_ACTIVATE_BOOK,
    BTN_DEACTIVATE_BOOK,
    BTN_MEMBERS_LIST,
]

USER_BUTTONS = [
    BTN_ACTIVE_BOOKS,
    BTN_MY_BOOKS,
    BTN_TODAY_REPORT,
    BTN_MY_REPORTS,
    BTN_ANSWER_QUESTIONS,
    BTN_MEMBERS_LIST,
]

ALL_MENU_BUTTONS = ADMIN_BUTTONS + USER_BUTTONS

ADMIN_MENU = ReplyKeyboardMarkup(
    [
        [BTN_NEW_BOOK, BTN_SCHEDULE],
        [BTN_QUESTIONS, BTN_DAY_REPORT],
        [BTN_QUESTION_REPORT, BTN_LIST_BOOKS],
        [BTN_EDIT_BOOK, BTN_DELETE_BOOK],
        [BTN_ACTIVATE_BOOK, BTN_DEACTIVATE_BOOK],
        [BTN_MEMBERS_LIST],
    ],
    resize_keyboard=True,
)

USER_MENU = ReplyKeyboardMarkup(
    [
        [BTN_ACTIVE_BOOKS, BTN_MY_BOOKS],
        [BTN_TODAY_REPORT, BTN_MY_REPORTS],
        [BTN_ANSWER_QUESTIONS, BTN_MEMBERS_LIST],
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


def books_with_status_kb(books, prefix: str, status_labels: dict) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                f"{b['title']} — {status_labels.get(b['status'], b['status'])}",
                callback_data=f"{prefix}:{b['id']}",
            )
        ]
        for b in books
    ]
    return InlineKeyboardMarkup(rows)


def fields_kb(fields, prefix: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(label, callback_data=f"{prefix}:{key}")]
        for key, label in fields
    ]
    return InlineKeyboardMarkup(rows)


def reading_days_kb(days, prefix: str, status_by_day=None) -> InlineKeyboardMarkup:
    rows = []
    status_by_day = status_by_day or {}

    for d in days:
        suffix = ""
        if d["id"] in status_by_day:
            suffix = f" | {status_by_day[d['id']]}"
        rows.append(
            [
                InlineKeyboardButton(
                    f"روز {d['day_index']} - {d['jalali_date']}{suffix}",
                    callback_data=f"{prefix}:{d['id']}",
                )
            ]
        )

    return InlineKeyboardMarkup(rows)


def questions_kb(questions, prefix: str) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                f"سوال {q['order_index']}", callback_data=f"{prefix}:{q['id']}"
            )
        ]
        for q in questions
    ]
    return InlineKeyboardMarkup(rows)


def question_manage_kb(questions) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                f"❓ {q['order_index']} - {q['text'][:55]}",
                callback_data=f"q_item:{q['id']}",
            )
        ]
        for q in questions
    ]
    rows.append(
        [InlineKeyboardButton("➕ سوال جدید", callback_data="q_action:add")]
    )
    rows.append(
        [InlineKeyboardButton("✅ پایان", callback_data="q_action:done")]
    )
    return InlineKeyboardMarkup(rows)


def question_actions_kb(question_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✏️ ویرایش", callback_data=f"q_edit:{question_id}"
                ),
                InlineKeyboardButton(
                    "🗑 حذف", callback_data=f"q_delete:{question_id}"
                ),
            ],
            [InlineKeyboardButton("↩️ بازگشت", callback_data="q_action:back")],
        ]
    )


def confirm_delete_question_kb(question_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🗑 بله، حذف کن",
                    callback_data=f"q_delconfirm:yes:{question_id}",
                ),
                InlineKeyboardButton(
                    "↩️ انصراف",
                    callback_data=f"q_delconfirm:no:{question_id}",
                ),
            ]
        ]
    )


def confirm_kb(prefix: str, ref_id) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ تأیید و ثبت", callback_data=f"{prefix}:confirm:{ref_id}"
                ),
                InlineKeyboardButton(
                    "❌ انصراف", callback_data=f"{prefix}:cancel:{ref_id}"
                ),
            ]
        ]
    )