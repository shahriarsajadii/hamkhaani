# -*- coding: utf-8 -*-
"""
تنظیمات عمومی ربات که به هیچ کتاب خاصی وابسته نیستند.

فعلاً فقط شامل ثبت گروه «تحلیل کتاب» است: گروهی معمولی (بدون تاپیک) که
نتیجه‌ی نظرسنجی‌های انتخاب کتاب ماهانه در آن پست می‌شود.
"""
import logging

from telegram import Update
from telegram.ext import ContextTypes

import database as db
from handlers.common import is_admin

logger = logging.getLogger(__name__)

# کلید ذخیره‌سازی chat_id گروه «تحلیل کتاب» در جدول settings
ANALYSIS_GROUP_KEY = "analysis_group_chat_id"


async def set_analysis_group_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    فقط ادمین، داخل خودِ گروه «تحلیل کتاب» (بدون نیاز به تاپیک) این دستور را می‌فرستد:
        /setanalysisgroup
    تا آن گروه به‌عنوان مقصد پیام نتیجه‌ی نظرسنجی‌های انتخاب کتاب ثبت شود.
    """
    if not is_admin(update.effective_user.id):
        return

    msg = update.message
    if msg.chat.type not in ("group", "supergroup"):
        await msg.reply_text(
            "این دستور فقط باید داخل خودِ گروه «تحلیل کتاب» فرستاده بشه."
        )
        return

    chat_id = msg.chat_id
    db.set_setting(ANALYSIS_GROUP_KEY, str(chat_id))

    logger.info("گروه تحلیل کتاب ثبت شد: chat_id=%s", chat_id)

    await msg.reply_text(
        "✅ این گروه به‌عنوان «گروه تحلیل کتاب» ثبت شد.\n"
        "از این به بعد، وقتی نظرسنجی انتخاب کتاب از پنل ادمین بسته بشه، "
        "نتیجه همینجا پست می‌شه."
    )
