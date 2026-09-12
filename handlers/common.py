# -*- coding: utf-8 -*-
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

import database as db
from config import ADMIN_IDS
from utils.keyboards import ADMIN_MENU, USER_MENU


def is_admin(telegram_id: int) -> bool:
    return telegram_id in ADMIN_IDS


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    tg_user = update.effective_user
    menu = ADMIN_MENU if is_admin(tg_user.id) else USER_MENU
    await update.message.reply_text("عملیات لغو شد.", reply_markup=menu)
    return ConversationHandler.END


async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    menu = ADMIN_MENU if is_admin(tg_user.id) else USER_MENU
    await update.message.reply_text(
        "متوجه نشدم 🤔 لطفاً از دکمه‌ های منو استفاده کن.", reply_markup=menu
    )
