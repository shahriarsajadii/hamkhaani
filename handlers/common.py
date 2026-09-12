# -*- coding: utf-8 -*-
import re

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, filters

import database as db
from config import ADMIN_IDS
from utils.keyboards import ADMIN_MENU, USER_MENU, ALL_MENU_BUTTONS

# پیام‌های متنی‌ای که داخل state های گفتگو به عنوان «ورودی کاربر» پذیرفته می‌شوند:
# دکمه‌های منو از این فیلتر خارج‌اند تا هیچ‌وقت به‌عنوان عنوان کتاب/پاسخ ذخیره نشوند.
MENU_PATTERN = "^(" + "|".join(re.escape(b) for b in ALL_MENU_BUTTONS) + ")$"
TEXT_INPUT = filters.TEXT & ~filters.COMMAND & ~filters.Regex(MENU_PATTERN)


def button_filter(text: str):
    """فیلتر دقیق برای یک دکمه‌ی منو."""
    return filters.Regex("^" + re.escape(text) + "$")


def is_admin(telegram_id: int) -> bool:
    return telegram_id in ADMIN_IDS


def menu_for(telegram_id: int):
    return ADMIN_MENU if is_admin(telegram_id) else USER_MENU


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    tg_user = update.effective_user
    db.upsert_user(tg_user.id, tg_user.username, tg_user.full_name)

    if is_admin(tg_user.id):
        await update.message.reply_text(
            f"سلام {tg_user.first_name} 👋\nبه پنل مدیریت ربات همخوانی خوش اومدی.",
            reply_markup=ADMIN_MENU,
        )
    else:
        await update.message.reply_text(
            f"سلام {tg_user.first_name} 👋\nبه ربات همخوانی خوش اومدی.\n"
            "از منوی پایین می‌تونی توی کتاب ‌ها ثبت ‌نام کنی و پیشرفتت رو گزارش بدی.",
            reply_markup=USER_MENU,
        )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "عملیات لغو شد. از منو یه گزینه انتخاب کن 👇",
        reply_markup=menu_for(update.effective_user.id),
    )
    return ConversationHandler.END


async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "متوجه نشدم 🤔 لطفاً از دکمه‌ های منو استفاده کن.",
        reply_markup=menu_for(update.effective_user.id),
    )


async def end_and_show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """پایان دادن به گفتگو همراه با نمایش دوباره منو."""
    context.user_data.clear()
    chat_id = update.effective_chat.id
    await context.bot.send_message(
        chat_id=chat_id, text=text, reply_markup=menu_for(update.effective_user.id)
    )
    return ConversationHandler.END
