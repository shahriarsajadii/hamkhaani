
import logging
from telegram.ext import Application, CommandHandler

import database as db
from config import BOT_TOKEN
from handlers.common import start, cancel, unknown_message
from handlers.admin.book import book_conv_handler, activate_book_conv_handler, set_topic_command
from handlers.admin import (
    schedule_conv_handler,
    questions_conv_handler,
    day_report_conv_handler,
    question_report_conv_handler,
    list_books_handler,
)
from handlers.user import (
    registration_conv_handler,
    my_books_handler,
    today_report_handler,
    tracking_callback_handler,
    answers_conv_handler,
)
from scheduler import setup_jobs

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    db.init_db()

    application = Application.builder().token(BOT_TOKEN).build()

    # عمومی
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CommandHandler("settopic", set_topic_command))

    # ادمین
    application.add_handler(book_conv_handler)
    application.add_handler(activate_book_conv_handler)
    application.add_handler(schedule_conv_handler)
    application.add_handler(questions_conv_handler)
    application.add_handler(day_report_conv_handler)
    application.add_handler(question_report_conv_handler)
    application.add_handler(CommandHandler("books", list_books_handler))
    from telegram.ext import MessageHandler, filters
    application.add_handler(MessageHandler(filters.Regex("^📚 لیست کتاب‌ها$"), list_books_handler))

    # کاربر
    application.add_handler(registration_conv_handler)
    application.add_handler(MessageHandler(filters.Regex("^📖 کتاب‌های من$"), my_books_handler))
    application.add_handler(today_report_handler)
    application.add_handler(tracking_callback_handler)
    application.add_handler(answers_conv_handler)

    # فال‌بک برای پیام‌های ناشناخته (باید آخر از همه اضافه بشه)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_message))

    # جاب روزانه یادآوری
    setup_jobs(application)

    logger.info("ربات در حال اجراست...")
    application.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
