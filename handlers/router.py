# -*- coding: utf-8 -*-
"""
همه‌ی مسیرهای ربات داخل یک ConversationHandler واحد با allow_reentry=True جمع شده‌اند.

مشکل «دکمه شیشه‌ای از پیام قدیمی کار نمی‌کند»:
  وقتی کاربر مثلاً در state DAYREP_CHOOSE_BOOK است (دکمه انتخاب کتاب نمایش دارد)،
  ناگهان یک دکمه منو دیگر می‌زند (مثلاً «تعیین برنامه»). ConversationHandler با
  allow_reentry=True وارد state جدید SCHED_CHOOSE_BOOK می‌شود.
  حالا اگر کاربر دکمه شیشه‌ای قدیمی (arep_book: یا rep_book: ...) را بزند،
  handler آن pattern در state جاری (SCHED_CHOOSE_BOOK) تعریف نشده → تلگرام spinner
  می‌دهد و هیچ اتفاقی نمی‌افتد.

راه‌حل:
  تمام CallbackQueryHandler های موجود در هر state را به همه‌ی state های دیگر
  هم اضافه می‌کنیم. به این ترتیب هر callback در هر state که کاربر باشد پاسخ
  می‌گیرد.
  علاوه بر این یک «stale_callback_handler» عمومی اضافه می‌کنیم که هر callback
  ناشناخته را با یک پیام ساده پاسخ دهد تا spinner باقی نماند.
"""
from telegram import Update
from telegram.ext import CommandHandler, ConversationHandler, CallbackQueryHandler, ContextTypes

from handlers.common import start, cancel
from handlers.admin import book, schedule, questions, reports
from handlers.user import registration, tracking, answers, members

MODULES = (book, schedule, questions, reports, registration, tracking, answers, members)


async def stale_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    هر callback query که به هیچ handler دیگری نرسید را اینجا می‌گیریم.
    فقط spinner را برمی‌داریم و یک پیام کوتاه به کاربر می‌دهیم.
    """
    query = update.callback_query
    if query:
        await query.answer("این دکمه دیگه فعال نیست. از منو دوباره شروع کن 🔄")


def build_conversation() -> ConversationHandler:
    entry_points = []
    all_states: dict = {}

    # ابتدا همه state های هر ماژول را جمع می‌کنیم
    for module in MODULES:
        entry_points.extend(module.ENTRY_POINTS)
        all_states.update(module.STATES)

    # همه CallbackQueryHandler هایی که در هر state وجود دارند را یکجا جمع می‌کنیم
    all_callback_handlers = []
    for handlers_list in all_states.values():
        for h in handlers_list:
            if isinstance(h, CallbackQueryHandler):
                all_callback_handlers.append(h)

    # یک handler catch-all برای callback های ناشناخته/قدیمی
    all_callback_handlers.append(
        CallbackQueryHandler(stale_callback_handler)
    )

    # هر state را با تمام callback handler های سیستم غنی می‌کنیم
    # (handler های اختصاصی state اول اضافه می‌شوند تا اولویت داشته باشند)
    merged_states: dict = {}
    for state, handlers_list in all_states.items():
        # handler های اختصاصی این state
        own = list(handlers_list)
        # callback های state های دیگر (بدون تکرار)
        extra = [h for h in all_callback_handlers if h not in own]
        merged_states[state] = own + extra

    entry_points = [CommandHandler("start", start), CommandHandler("cancel", cancel)] + entry_points

    return ConversationHandler(
        entry_points=entry_points,
        states=merged_states,
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("start", start),
            CallbackQueryHandler(stale_callback_handler),
        ],
        allow_reentry=True,
    )