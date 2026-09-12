
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters

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


def main():
    db.init_db()

    application = Application.builder().token(BOT_TOKEN).build()

    # گفتگوی واحد ربات (منوی ادمین و کاربر)
    application.add_handler(build_conversation())

    # دستورات مستقل
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CommandHandler("settopic", set_topic_command))

    # پاسخ بله/خیر یادآوری روزانه
    application.add_handler(tracking_callback_handler)

    # فال‌بک برای پیام‌های ناشناخته (باید آخر از همه اضافه بشه)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_message))

    # جاب روزانه یادآوری
    setup_jobs(application)

    logger.info("ربات در حال اجراست...")
    application.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
