import logging
import sys

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
from config import BOT_TOKEN, BOT_NAME, BOT_DESCRIPTION, BOT_SHORT_DESCRIPTION
from handlers.common import start, cancel, unknown_message
from handlers.admin.book import set_topic_command
from handlers.router import build_conversation
from handlers.user.tracking import tracking_callback_handler
from scheduler import setup_jobs

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# کاهش لاگ‌های پر-سروصدای httpx
logging.getLogger("httpx").setLevel(logging.WARNING)


async def group_guard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    در گروه‌ها فقط /settopic مجاز است.
    هر پیام یا دستور دیگری از کاربران (حتی ادمین) نادیده گرفته می‌شود.
    """
    return


async def group_callback_guard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    در گروه‌ها هیچ callback query ای نباید پاسخ داده شود.
    اگر کسی روی inline button در گروه کلیک کند، ربات ساکت می‌ماند.
    """
    query = update.callback_query
    if query and update.effective_chat and update.effective_chat.type in ("group", "supergroup"):
        try:
            await query.answer()
        except Exception:
            pass
    return


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """
    هندلر مرکزی خطا — از کرش بات جلوگیری می‌کند و خطاها رو لاگ می‌کند.
    """
    logger.error("خطای ناگرفته‌شده:", exc_info=context.error)


async def post_init(application: Application):
    """
    - در گروه‌ها منوی دستورات را خالی می‌کنیم.
    - نام و دیسکریپشن ربات را از env ست می‌کنیم (اگر تعریف شده باشند).
    """
    try:
        await application.bot.set_my_commands(
            [], scope=BotCommandScopeAllGroupChats()
        )
    except Exception as e:
        logger.warning("تنظیم منوی دستورات گروه با خطا مواجه شد: %s", e)

    if BOT_NAME:
        try:
            await application.bot.set_my_name(BOT_NAME)
            logger.info("نام ربات به «%s» تغییر کرد.", BOT_NAME)
        except Exception as e:
            logger.warning("تنظیم نام ربات با خطا مواجه شد: %s", e)

    if BOT_DESCRIPTION:
        try:
            await application.bot.set_my_description(BOT_DESCRIPTION)
            logger.info("دیسکریپشن ربات ست شد.")
        except Exception as e:
            logger.warning("تنظیم دیسکریپشن ربات با خطا مواجه شد: %s", e)

    if BOT_SHORT_DESCRIPTION:
        try:
            await application.bot.set_my_short_description(BOT_SHORT_DESCRIPTION)
            logger.info("توضیح کوتاه ربات ست شد.")
        except Exception as e:
            logger.warning("تنظیم توضیح کوتاه ربات با خطا مواجه شد: %s", e)


def main():
    db.init_db()

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        # تنظیمات شبکه برای استیبیلیتی بیشتر
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .pool_timeout(30)
        .build()
    )

    # هندلر مرکزی خطا — مهم‌ترین بخش استیبیلیتی
    application.add_error_handler(error_handler)

    # فیلتر پیام‌های گروهی: همه‌چیز رو بلوک کن به‌جز /settopic
    group_filter = filters.ChatType.GROUPS & ~filters.Regex(r"^/settopic")
    application.add_handler(
        MessageHandler(group_filter, group_guard),
        group=-1,
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

    setup_jobs(application)

    logger.info("ربات در حال اجراست...")
    application.run_polling(
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=True,
        # در صورت قطع شدن اتصال، هر 5 ثانیه یک‌بار سعی کند
        poll_interval=1.0,
    )


if __name__ == "__main__":
    main()