# -*- coding: utf-8 -*-
"""
همه‌ی مسیرهای ربات داخل یک ConversationHandler واحد با allow_reentry=True جمع شده‌اند.

چرا؟ چون قبلاً هر مسیر ConversationHandler جدا داشت و اگر کاربر وسط یک مسیر رهاش می‌کرد،
پیام بعدی‌اش (مثلاً دکمه «📊 گزارش روز») به‌عنوان ورودیِ مسیر نیمه‌کاره خوانده می‌شد.
با یک گفتگوی واحد، دکمه‌های منو همیشه entry point هستند و هر لحظه گفتگوی قبلی را ریست می‌کنند.
"""
from telegram.ext import CommandHandler, ConversationHandler

from handlers.common import start, cancel
from handlers.admin import book, schedule, questions, reports
from handlers.user import registration, tracking, answers

MODULES = (book, schedule, questions, reports, registration, tracking, answers)


def build_conversation() -> ConversationHandler:
    entry_points = []
    states = {}
    for module in MODULES:
        entry_points.extend(module.ENTRY_POINTS)
        states.update(module.STATES)

    # /start و /cancel هم باید در هر لحظه گفتگو را تمام کنند.
    entry_points = [CommandHandler("start", start), CommandHandler("cancel", cancel)] + entry_points

    return ConversationHandler(
        entry_points=entry_points,
        states=states,
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start)],
        allow_reentry=True,
    )
