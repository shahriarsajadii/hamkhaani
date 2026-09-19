# -*- coding: utf-8 -*-
"""
جریان پاسخ به سوالات کتاب:

- کاربر کتاب را انتخاب می‌کند.
- لیست سوالات را با وضعیت پاسخ می‌بیند (پاسخ داده / پاسخ نداده).
- روی هر سوال کلیک می‌کند، پاسخ خود را وارد یا ویرایش می‌کند.
- وقتی حداقل یک سوال پاسخ داده شد، دکمه «📤 ارسال نهایی پاسخ‌ها» ظاهر می‌شود.
- با زدن این دکمه، پاسخ‌ها ثبت نهایی می‌شوند و دیگر قابل ویرایش نیستند.
- بعد از ارسال نهایی، کاربر می‌تواند سوالات و پاسخ‌های خودش را ببیند.
"""
import logging

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
)

import database as db
from utils.keyboards import books_kb, BTN_ANSWER_QUESTIONS
from utils.formatting import format_answer_submitted_notification
from handlers.common import TEXT_INPUT, end_and_show_menu, button_filter
from handlers.states import S

logger = logging.getLogger(__name__)


# دکمه‌ی بازگشت به لیست سوالات (در حالت پاسخ‌دهی/ویرایش)
BACK_KB = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(
                "↩️ بازگشت به لیست سوالات",
                callback_data="ans_back",
            )
        ]
    ]
)


def _answers_by_question(user_id: int, book_id: int) -> dict:
    rows = db.get_user_answers_for_book(user_id, book_id)
    return {r["question_id"]: r for r in rows}


def _answers_list_text(book, questions, answers_by_q, submitted: bool) -> str:
    lines = [f"📖 «{book['title']}»", ""]

    if submitted:
        lines.append("✅ پاسخ‌های شما ثبت نهایی شده و قابل ویرایش نیست.")
        lines.append("")
        lines.append("لیست سوالات و پاسخ‌های شما:")
    else:
        lines.append("روی هر سوال کلیک کن و پاسخ خودت رو وارد کن.")
        lines.append("بعد از جواب دادن به حداقل یه سوال، می‌تونی ارسال نهایی کنی.")
    lines.append("")

    for q in questions:
        ans = answers_by_q.get(q["id"])
        lines.append(f"❓ سوال {q['order_index']}: {q['text']}")
        if ans:
            lines.append(f"   ✅ پاسخ: {ans['text']}")
        else:
            lines.append("   ⏳ پاسخ داده نشده")
        lines.append("")

    return "\n".join(lines).rstrip()


def _answers_list_kb(questions, answers_by_q, submitted: bool) -> InlineKeyboardMarkup:
    rows = []
    for q in questions:
        ans = answers_by_q.get(q["id"])
        if ans:
            preview = ans["text"].split("\n")[0][:35]
            if len(ans["text"]) > 35:
                preview += "…"
            label = f"✅ سوال {q['order_index']}: {preview}"
        else:
            label = f"⏳ سوال {q['order_index']}: پاسخ داده نشده"
        rows.append(
            [InlineKeyboardButton(label, callback_data=f"ans_item:{q['id']}")]
        )

    # دکمه ارسال نهایی: حداقل یک سوال جواب داده شده باشد کافی است
    if not submitted and len(answers_by_q) >= 1:
        rows.append(
            [
                InlineKeyboardButton(
                    "📤 ارسال نهایی پاسخ‌ها",
                    callback_data="ans_submit",
                )
            ]
        )

    return InlineKeyboardMarkup(rows)


# ---------------------------------------------------------- start flow ----

async def answers_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    user_row = db.get_user_by_telegram_id(update.effective_user.id)
    if not user_row:
        return await end_and_show_menu(
            update, context, "اول باید توی یه کتاب ثبت‌نام کنی."
        )

    books = db.get_user_books(user_row["id"])
    books_with_q = [b for b in books if db.get_questions(b["id"])]

    if not books_with_q:
        return await end_and_show_menu(
            update, context, "هنوز سوالی برای کتاب‌های تو تعریف نشده."
        )

    await update.message.reply_text(
        "کتاب موردنظر رو انتخاب کن:", reply_markup=books_kb(books_with_q, "ans_book")
    )
    return S.ANS_CHOOSE_BOOK


async def answers_choose_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        book_id = int(query.data.split(":")[1])
    except (IndexError, ValueError):
        await query.edit_message_text("شناسه نامعتبر.")
        return ConversationHandler.END

    user_row = db.get_user_by_telegram_id(update.effective_user.id)
    if not user_row:
        await query.edit_message_text("کاربر پیدا نشد.")
        return ConversationHandler.END

    book = db.get_book(book_id)
    if not book:
        await query.edit_message_text("کتاب پیدا نشد.")
        return ConversationHandler.END

    if not db.is_user_registered(book_id, user_row["id"]):
        await query.edit_message_text("توی این کتاب ثبت‌نام نکردی.")
        return ConversationHandler.END

    questions = db.get_questions(book_id)
    if not questions:
        await query.edit_message_text("برای این کتاب سوالی ثبت نشده.")
        return ConversationHandler.END

    if not db.can_user_answer_book(user_row["id"], book_id):
        await query.edit_message_text(
            f"⛔ هنوز امکان پاسخ به سوالات «{book['title']}» رو نداری.\n\n"
            "برای پاسخ‌دادن باید گزارش تمام روزهای برنامه ثبت شده باشه "
            "و وضعیت همهٔ روزها «خواندم» باشه."
        )
        return ConversationHandler.END

    context.user_data["ans_book_id"] = book_id
    context.user_data["ans_user_id"] = user_row["id"]
    context.user_data.pop("ans_question_id", None)

    submitted = db.is_answers_submitted(user_row["id"], book_id)
    answers_by_q = _answers_by_question(user_row["id"], book_id)

    await query.edit_message_text(
        _answers_list_text(book, questions, answers_by_q, submitted),
        reply_markup=_answers_list_kb(questions, answers_by_q, submitted),
    )
    return S.ANS_MANAGE_LIST


# ----------------------------------------------------- manage list view ----

async def answers_manage_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = context.user_data.get("ans_user_id")
    book_id = context.user_data.get("ans_book_id")
    book = db.get_book(book_id) if book_id else None

    if not book or not user_id:
        await query.edit_message_text("اطلاعات پیدا نشد.")
        return ConversationHandler.END

    # FIX: sqlite3.Row does not support .get() — convert to dict
    book = dict(book)

    data = query.data or ""
    questions = db.get_questions(book_id)
    submitted = db.is_answers_submitted(user_id, book_id)

    # بازگشت به لیست
    if data == "ans_back":
        context.user_data.pop("ans_question_id", None)
        answers_by_q = _answers_by_question(user_id, book_id)
        await query.edit_message_text(
            _answers_list_text(book, questions, answers_by_q, submitted),
            reply_markup=_answers_list_kb(questions, answers_by_q, submitted),
        )
        return S.ANS_MANAGE_LIST

    # ارسال نهایی
    if data == "ans_submit":
        if submitted:
            await query.edit_message_text(
                "ℹ️ پاسخ‌های شما قبلاً ثبت نهایی شده بود.",
                reply_markup=_answers_list_kb(
                    questions, _answers_by_question(user_id, book_id), True
                ),
            )
            return S.ANS_MANAGE_LIST

        answers_by_q = _answers_by_question(user_id, book_id)

        # حداقل یک سوال باید جواب داده شده باشد
        if len(answers_by_q) == 0:
            await query.edit_message_text(
                "⚠️ باید حداقل به یه سوال پاسخ بدی تا بتونی ارسال نهایی کنی.",
                reply_markup=_answers_list_kb(questions, answers_by_q, False),
            )
            return S.ANS_MANAGE_LIST

        db.submit_answers(user_id, book_id)

        # اعلام در گروه کتاب
        tg_user = update.effective_user
        group_chat_id = book.get("group_chat_id")
        if group_chat_id:
            try:
                answered_count = len(answers_by_q)
                total_count = len(questions)
                notification = format_answer_submitted_notification(
                    book["title"],
                    tg_user.full_name or tg_user.first_name,
                    tg_user.username,
                    answered_count,
                    total_count,
                )
                await context.bot.send_message(
                    chat_id=group_chat_id,
                    message_thread_id=book.get("topic_pigiri_id"),
                    text=notification,
                )
            except Exception as e:
                logger.warning("خطا در اعلام گروه پس از ارسال پاسخ: %s", e)

        await query.edit_message_text(
            "🎉 پاسخ‌های شما با موفقیت ثبت نهایی شد. متشکریم!\n\n"
            + _answers_list_text(book, questions, answers_by_q, True),
            reply_markup=_answers_list_kb(questions, answers_by_q, True),
        )
        return S.ANS_MANAGE_LIST

    # ans_item:<id> — انتخاب یک سوال
    if data.startswith("ans_item:"):
        try:
            question_id = int(data.split(":")[1])
        except (IndexError, ValueError):
            await query.edit_message_text("شناسه نامعتبر.")
            return S.ANS_MANAGE_LIST

        question = db.get_question(question_id)
        if not question:
            await query.edit_message_text("سوال پیدا نشد.")
            return S.ANS_MANAGE_LIST

        context.user_data["ans_question_id"] = question_id

        # اگر پاسخ‌ها قبلاً نهایی شده، فقط نمایش بده
        if submitted:
            ans = db.get_user_answer_for_question(user_id, question_id)
            ans_text = ans["text"] if ans else "(بدون پاسخ)"
            await query.edit_message_text(
                f"❓ {question['text']}\n\n"
                f"✅ پاسخ نهایی شما:\n{ans_text}\n\n"
                "(این پاسخ ثبت نهایی شده و قابل ویرایش نیست.)",
                reply_markup=BACK_KB,
            )
            return S.ANS_MANAGE_LIST

        # حالت ویرایش/پاسخ جدید
        ans = db.get_user_answer_for_question(user_id, question_id)
        if ans:
            prompt = (
                f"❓ {question['text']}\n\n"
                f"✅ پاسخ فعلی:\n{ans['text']}\n\n"
                "پاسخ جدید رو بفرست (یا /cancel بزن):"
            )
        else:
            prompt = (
                f"❓ {question['text']}\n\n"
                "پاسخ خودت رو بنویس (یا /cancel بزن):"
            )

        await query.edit_message_text(prompt, reply_markup=BACK_KB)
        return S.ANS_EDIT_TEXT

    return S.ANS_MANAGE_LIST


# --------------------------------------------------------- edit / answer --

async def answers_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = context.user_data.get("ans_user_id")
    book_id = context.user_data.get("ans_book_id")
    question_id = context.user_data.get("ans_question_id")

    if not all([user_id, book_id, question_id]):
        return await end_and_show_menu(
            update, context, "مشکلی پیش اومد، دوباره از منو شروع کن."
        )

    if db.is_answers_submitted(user_id, book_id):
        return await end_and_show_menu(
            update, context, "پاسخ‌های شما قبلاً ثبت نهایی شده."
        )

    if not db.can_user_answer_book(user_id, book_id):
        return await end_and_show_menu(
            update, context, "فعلاً امکان پاسخ‌دادن به سوالات این کتاب وجود نداره."
        )

    text = update.message.text.strip()
    if not text:
        await update.message.reply_text(
            "پاسخ نمی‌تونه خالی باشه.", reply_markup=BACK_KB
        )
        return S.ANS_EDIT_TEXT

    try:
        db.save_answer(question_id, user_id, text)
    except ValueError as e:
        await update.message.reply_text(str(e), reply_markup=BACK_KB)
        return S.ANS_EDIT_TEXT

    context.user_data.pop("ans_question_id", None)

    book = db.get_book(book_id)
    questions = db.get_questions(book_id)
    answers_by_q = _answers_by_question(user_id, book_id)

    await update.message.reply_text(
        "✅ پاسخ ثبت شد.\n\n"
        + _answers_list_text(book, questions, answers_by_q, False),
        reply_markup=_answers_list_kb(questions, answers_by_q, False),
    )
    return S.ANS_MANAGE_LIST


# --------------------------------------------------------- exports ----

ENTRY_POINTS = [
    MessageHandler(button_filter(BTN_ANSWER_QUESTIONS), answers_start)
]

STATES = {
    S.ANS_CHOOSE_BOOK: [
        CallbackQueryHandler(answers_choose_book, pattern=r"^ans_book:")
    ],
    S.ANS_MANAGE_LIST: [
        CallbackQueryHandler(
            answers_manage_list,
            pattern=r"^ans_(item:\d+|submit|back)$",
        )
    ],
    S.ANS_EDIT_TEXT: [
        MessageHandler(TEXT_INPUT, answers_receive),
        CallbackQueryHandler(answers_manage_list, pattern=r"^ans_back$"),
    ],
}