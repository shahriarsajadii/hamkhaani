# -*- coding: utf-8 -*-
"""
تمام state های گفتگوها در یک enum یکتا جمع شده‌اند.

دلیلش این است که کل ربات یک ConversationHandler واحد (با allow_reentry) دارد؛
این‌طوری هر دکمه‌ی منو در هر لحظه کار می‌کند و هیچ‌وقت گیر گفتگوی نیمه‌کاره‌ی قبلی نمی‌ماند.
"""
from enum import IntEnum, auto


class S(IntEnum):
    # ساخت کتاب
    BOOK_TITLE = auto()
    BOOK_AUTHOR = auto()
    BOOK_DESCRIPTION = auto()
    BOOK_PAGES = auto()
    BOOK_PDF_PAGES = auto()

    # ویرایش کتاب
    EDIT_CHOOSE_BOOK = auto()
    EDIT_CHOOSE_FIELD = auto()
    EDIT_VALUE = auto()

    # حذف کتاب
    DELETE_CHOOSE_BOOK = auto()
    DELETE_CONFIRM = auto()

    # فعال‌سازی کتاب
    ACTIVATE_CHOOSE_BOOK = auto()

    # برنامه همخوانی
    SCHED_CHOOSE_BOOK = auto()
    SCHED_ACTION = auto()
    SCHED_ASK_START_DATE = auto()
    SCHED_ASK_PAGES_PER_DAY = auto()
    SCHED_CONFIRM = auto()
    SCHED_MANUAL_DATE = auto()
    SCHED_MANUAL_BOOK_PAGES = auto()
    SCHED_MANUAL_PDF_PAGES = auto()
    SCHED_MANUAL_CONTINUE = auto()

    # سوالات
    Q_CHOOSE_BOOK = auto()
    Q_ASK_TEXT = auto()
    Q_CONTINUE = auto()

    # گزارش روز
    DAYREP_CHOOSE_BOOK = auto()
    DAYREP_CHOOSE_DAY = auto()

    # گزارش سوالات
    QREP_CHOOSE_BOOK = auto()
    QREP_CHOOSE_QUESTION = auto()

    # ثبت‌نام کاربر
    REG_CHOOSE_BOOK = auto()

    # پاسخ کاربر به سوالات
    ANS_CHOOSE_BOOK = auto()
    ANS_ANSWERING = auto()
