# -*- coding: utf-8 -*-
"""
مدیریت نظرسنجی انتخاب کتاب (پنل ادمین).

در هر لحظه حداکثر یک نظرسنجی «باز» وجود دارد. تا وقتی باز است، کاربرها از
منوی خودشون («📚 پیشنهاد کتاب») می‌تونن یک کتاب پیشنهاد بدن (و تا نظرسنجی
باز است می‌تونن پیشنهادشون رو عوض کنن).

وقتی نظرسنجی باز می‌شود:
- یک پیام اطلاع‌رسانی ثابت («نظرسنجی باز شد...») در گروه «تحلیل کتاب» پست می‌شود.
- زیر آن، یک پیام «زنده» با لیست پیشنهادها پست می‌شود که شناسه‌اش ذخیره می‌شود
  و با هر پیشنهاد جدید/تغییریافته (توسط refresh_group_poll_message) ویرایش می‌شود.

ادمین از این بخش می‌تونه:
- نظرسنجی جدید باز کنه (به شرطی که گروه «تحلیل کتاب» با /setanalysisgroup ثبت شده باشه)
- لیست پیشنهادهای نظرسنجی جاری/آخرین نظرسنجی رو ببینه
- نظرسنجی رو ببنده؛ با بستن، همون پیام زنده در گروه «بسته شد» می‌خوره
"""
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
)

import database as db
from utils.keyboards import BTN_BOOK_POLL
from utils.formatting import format_poll_group_message, format_poll_admin_list
from handlers.common import is_admin, end_and_show_menu, button_filter
from handlers.states import S
from handlers.admin.settings import ANALYSIS_GROUP_KEY

logger = logging.getLogger(__name__)


async def refresh_group_poll_message(context: ContextTypes.DEFAULT_TYPE, poll):
    """
    پیام «زنده»ی نظرسنجی را در گروه «تحلیل کتاب» به‌روزرسانی می‌کند
    (یا اگر هنوز پیامی ساخته نشده/پاک شده، یک پیام جدید می‌فرستد).
    این تابع از پنل ادمین (باز/بستن نظرسنجی) و هم از فلوی «پیشنهاد کتاب»
    کاربر (هر بار پیشنهاد جدید/تغییریافته) صدا زده می‌شود.
    """
    group_chat_id = db.get_setting(ANALYSIS_GROUP_KEY)
    if not group_chat_id:
        return

    suggestions = db.get_poll_suggestions(poll["id"])
    text = format_poll_group_message(suggestions, closed=(poll["status"] != "open"))

    if poll["announcement_message_id"]:
        try:
            await context.bot.edit_message_text(
                chat_id=int(group_chat_id),
                message_id=poll["announcement_message_id"],
                text=text,
            )
            return
        except Exception as e:
            logger.warning(
                "نتونستم پیام زنده‌ی نظرسنجی #%s رو ویرایش کنم، پیام جدید می‌فرستم: %s",
                poll["id"], e,
            )

    try:
        sent = await context.bot.send_message(chat_id=int(group_chat_id), text=text)
        db.set_poll_announcement_message_id(poll["id"], sent.message_id)
    except Exception as e:
        logger.warning("نتونستم پیام زنده‌ی نظرسنجی رو بفرستم: %s", e)


def _poll_menu(poll):
    """متن و کیبورد منوی نظرسنجی را بر اساس وضعیت فعلی می‌سازد."""
    if poll and poll["status"] == "open":
        suggestions = db.get_poll_suggestions(poll["id"])
        text = (
            f"🗳 نظرسنجی #{poll['id']} الان بازه.\n"
            f"تعداد پیشنهادها تا الان: {len(suggestions)}"
        )
        rows = [
            [InlineKeyboardButton("📋 مشاهده لیست پیشنهادها", callback_data="poll_action:list")],
            [InlineKeyboardButton("🔴 بستن نظرسنجی و ارسال به گروه", callback_data="poll_action:close")],
        ]
    else:
        text = "🗳 در حال حاضر نظرسنجی بازی وجود نداره."
        rows = [
            [InlineKeyboardButton("🟢 باز کردن نظرسنجی جدید", callback_data="poll_action:open")],
        ]
        if db.get_latest_poll():
            rows.append(
                [InlineKeyboardButton("📋 مشاهده لیست آخرین نظرسنجی", callback_data="poll_action:list")]
            )
    rows.append([InlineKeyboardButton("✅ پایان", callback_data="poll_action:done")])
    return text, InlineKeyboardMarkup(rows)


async def poll_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END
    context.user_data.clear()
    text, kb = _poll_menu(db.get_open_poll())
    await update.message.reply_text(text, reply_markup=kb)
    return S.POLL_MENU


async def poll_menu_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data.split(":")[1]

    if action == "done":
        context.user_data.clear()
        await query.edit_message_text("✅ مدیریت نظرسنجی تمام شد.")
        return await end_and_show_menu(update, context, "برگشتیم به منو 👇")

    if action == "open":
        if db.get_open_poll():
            text, kb = _poll_menu(db.get_open_poll())
            await query.edit_message_text(
                "⚠️ همین الان یه نظرسنجی باز هست، اول اونو ببند.\n\n" + text,
                reply_markup=kb,
            )
            return S.POLL_MENU

        group_chat_id = db.get_setting(ANALYSIS_GROUP_KEY)
        if not group_chat_id:
            text, kb = _poll_menu(None)
            await query.edit_message_text(
                "⚠️ اول باید گروه «تحلیل کتاب» رو ثبت کنی.\n"
                "داخل خودِ اون گروه دستور /setanalysisgroup رو بفرست، بعد دوباره امتحان کن.\n\n"
                + text,
                reply_markup=kb,
            )
            return S.POLL_MENU

        # پیام ثابت اطلاع‌رسانی باز شدن نظرسنجی
        try:
            await context.bot.send_message(
                chat_id=int(group_chat_id),
                text=(
                    "📚 نظرسنجی انتخاب کتاب این ماه باز شد!\n"
                    "هر کی دوست داره یه کتاب پیشنهاد بده، بره پیوی ربات و از منو "
                    "«📚 پیشنهاد کتاب» رو بزنه."
                ),
            )
        except Exception as e:
            logger.warning(
                "نتونستم اعلان باز شدن نظرسنجی رو به گروه تحلیل کتاب بفرستم: %s", e
            )

        poll_id = db.create_book_poll()
        poll = db.get_poll(poll_id)
        # پیام «زنده»ی لیست پیشنهادها، زیر پیام بالا پست می‌شود و از این به بعد آپدیت می‌شود
        await refresh_group_poll_message(context, poll)

        text, kb = _poll_menu(db.get_poll(poll_id))
        await query.edit_message_text("✅ نظرسنجی جدید باز شد.\n\n" + text, reply_markup=kb)
        return S.POLL_MENU

    if action == "list":
        poll = db.get_open_poll() or db.get_latest_poll()
        if not poll:
            text, kb = _poll_menu(None)
            await query.edit_message_text(
                "هنوز هیچ نظرسنجی‌ای ساخته نشده.\n\n" + text, reply_markup=kb
            )
            return S.POLL_MENU

        suggestions = db.get_poll_suggestions(poll["id"])
        list_text = format_poll_admin_list(poll, suggestions)
        _, kb = _poll_menu(db.get_open_poll())
        await query.edit_message_text(list_text, reply_markup=kb)
        return S.POLL_MENU

    if action == "close":
        poll = db.get_open_poll()
        if not poll:
            text, kb = _poll_menu(None)
            await query.edit_message_text(
                "نظرسنجی بازی برای بستن وجود نداره.\n\n" + text, reply_markup=kb
            )
            return S.POLL_MENU

        suggestions = db.get_poll_suggestions(poll["id"])
        confirm_kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✅ بله، ببند و ارسال کن", callback_data=f"poll_close:yes:{poll['id']}"
                    ),
                    InlineKeyboardButton(
                        "↩️ انصراف", callback_data=f"poll_close:no:{poll['id']}"
                    ),
                ]
            ]
        )
        await query.edit_message_text(
            f"⚠️ نظرسنجی #{poll['id']} با {len(suggestions)} پیشنهاد بسته بشه و "
            "پیام گروه «تحلیل کتاب» به‌روزرسانی نهایی بشه؟",
            reply_markup=confirm_kb,
        )
        return S.POLL_CLOSE_CONFIRM

    text, kb = _poll_menu(db.get_open_poll())
    await query.edit_message_text(text, reply_markup=kb)
    return S.POLL_MENU


async def poll_close_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, answer, poll_id = query.data.split(":")
    poll_id = int(poll_id)

    if answer != "yes":
        text, kb = _poll_menu(db.get_poll(poll_id))
        await query.edit_message_text("↩️ بستن نظرسنجی لغو شد.\n\n" + text, reply_markup=kb)
        return S.POLL_MENU

    db.close_book_poll(poll_id)
    poll = db.get_poll(poll_id)

    group_chat_id = db.get_setting(ANALYSIS_GROUP_KEY)
    if group_chat_id:
        await refresh_group_poll_message(context, poll)
        result_text = "✅ نظرسنجی بسته شد و پیام گروه «تحلیل کتاب» به‌روزرسانی شد."
    else:
        suggestions = db.get_poll_suggestions(poll_id)
        result_text = (
            "✅ نظرسنجی بسته شد ولی گروه «تحلیل کتاب» هنوز ثبت نشده "
            "(با /setanalysisgroup ثبتش کن).\n\n"
            + format_poll_group_message(suggestions, closed=True)
        )

    await query.edit_message_text(result_text)
    return await end_and_show_menu(update, context, "برگشتیم به منو 👇")


ENTRY_POINTS = [MessageHandler(button_filter(BTN_BOOK_POLL), poll_start)]

STATES = {
    S.POLL_MENU: [CallbackQueryHandler(poll_menu_action, pattern="^poll_action:")],
    S.POLL_CLOSE_CONFIRM: [CallbackQueryHandler(poll_close_confirm, pattern="^poll_close:")],
}
