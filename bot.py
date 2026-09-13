import logging

from telegram import BotCommandScopeAllGroupChats
from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

import database as db
from config import BOT_TOKEN
from handlers.common import start, cancel, unknown_message
from handlers.admin.book import set_topic_command
from handlers.router import build_conversation
from handlers.user.tracking import tracking_callback_handler
from scheduler import setup_jobs

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


async def group_guard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    در گروه‌ها فقط /settopic مجاز است.
    هر پیام یا دستور دیگری از کاربران (حتی ادمین) نادیده گرفته می‌شود.
    """
    # این هندلر هیچ پاسخی نمی‌دهد - فقط آپدیت را می‌بلعد
    return


async def group_callback_guard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    در گروه‌ها هیچ callback query ای نباید پاسخ داده شود.
    اگر کسی روی inline button در گروه کلیک کند، ربات ساکت می‌ماند.
    """
    query = update.callback_query
    if query and update.effective_chat and update.effective_chat.type in ("group", "supergroup"):
        await query.answer()  # تلگرام رو از حالت loading در بیاره بدون هیچ پیامی
    return


async def post_init(application: Application):
    """
    در گروه‌ها منوی دستورات پایین صفحه را خالی می‌کنیم تا کاربران
    دکمه‌ی کامندها را نبینند. (فقط در پیوی دستورات نمایش داده می‌شوند.)
    """
    try:
        await application.bot.set_my_commands(
            [], scope=BotCommandScopeAllGroupChats()
        )
    except Exception as e:
        logger.warning("تنظیم منوی دستورات گروه با خطا مواجه شد: %s", e)


def main():
    db.init_db()

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # فیلتر پیام‌های گروهی: همه‌چیز رو بلوک کن به‌جز /settopic
    group_filter = filters.ChatType.GROUPS & ~filters.Regex(r"^/settopic")
    # این هندلر باید اول از همه اضافه بشه تا اولویت داشته باشه
    application.add_handler(
        MessageHandler(group_filter, group_guard),
        group=-1,  # group=-1 یعنی قبل از همه هندلرها بررسی می‌شه
    )
    # بلوک کردن همه‌ی callback query ها در گروه‌ها
    application.add_handler(
        CallbackQueryHandler(group_callback_guard, pattern=".*", block=True),
        group=-1,
    )

    # گفتگوی واحد ربات (فقط در پیوی کار می‌کند)
    application.add_handler(build_conversation())

    # دستورات مستقل
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CommandHandler("settopic", set_topic_command))

    # پاسخ «خواندم» از یادآوری روزانه یا دکمه inline
    application.add_handler(tracking_callback_handler)

    # فال‌بک برای پیام‌های ناشناخته - فقط در پیوی (private)
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, unknown_message)
    )

    # جاب‌های روزانه/شبانهhttps://t.me/hamkhaanibot
    setup_jobs(application)

    logger.info("ربات در حال اجراست...")
    application.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()