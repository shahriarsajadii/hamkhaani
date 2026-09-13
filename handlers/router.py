# -*- coding: utf-8 -*-
"""
همه‌ی مسیرهای ربات داخل یک ConversationHandler واحد با allow_reentry=True جمع شده‌اند.
"""
from telegram.ext import CommandHandler, ConversationHandler

from handlers.common import start, cancel
from handlers.admin import book, schedule, questions, reports
from handlers.user import registration, tracking, answers, members

MODULES = (book, schedule, questions, reports, registration, tracking, answers, members)


def build_conversation() -> ConversationHandler:
    entry_points = []
    states = {}
    for module in MODULES:
        entry_points.extend(module.ENTRY_POINTS)
        states.update(module.STATES)

    entry_points = [CommandHandler("start", start), CommandHandler("cancel", cancel)] + entry_points

    return ConversationHandler(
        entry_points=entry_points,
        states=states,
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start)],
        allow_reentry=True,
    )