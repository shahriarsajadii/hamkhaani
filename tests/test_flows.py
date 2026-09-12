# -*- coding: utf-8 -*-
"""تست‌های پایه‌ی ربات: ساخت برنامه، عملیات دیتابیس و رفتار لغو دستورات."""
import asyncio
import datetime

import jdatetime
import pytest
from telegram import (
    CallbackQuery,
    Chat,
    Message,
    MessageEntity,
    Update,
    User,
)
from telegram.ext import ApplicationBuilder, ExtBot

import config
import database as db
from handlers.router import build_conversation
from utils.schedule import generate_days

ADMIN_ID = sorted(config.ADMIN_IDS)[0]
SENT: list = []


async def _reply_text(self, text, **kwargs):
    SENT.append(text)


async def _edit_message_text(self, text, **kwargs):
    SENT.append(text)


async def _answer(self, *args, **kwargs):
    return True


Message.reply_text = _reply_text
CallbackQuery.edit_message_text = _edit_message_text
CallbackQuery.answer = _answer


class FakeBot(ExtBot):
    async def send_message(self, chat_id, text, **kwargs):
        SENT.append(text)

    async def initialize(self):
        self._initialized = True
        self._bot_user = User(id=99, first_name="bot", is_bot=True, username="testbot")


class Harness:
    def __init__(self):
        self.bot = FakeBot("123:ABC")
        self.app = ApplicationBuilder().bot(self.bot).updater(None).job_queue(None).build()
        self.app.add_handler(build_conversation())
        self.user = User(id=ADMIN_ID, first_name="Admin", is_bot=False)
        self.chat = Chat(id=ADMIN_ID, type="private")
        self.counter = 0

    async def start(self):
        await self.app.initialize()

    def _next_id(self):
        self.counter += 1
        return self.counter

    async def send(self, text):
        entities = (
            [MessageEntity(type="bot_command", offset=0, length=len(text))]
            if text.startswith("/")
            else None
        )
        msg = Message(
            message_id=self._next_id(),
            date=datetime.datetime.now(),
            chat=self.chat,
            from_user=self.user,
            text=text,
            entities=entities,
        )
        msg.set_bot(self.bot)
        await self.app.process_update(Update(update_id=self._next_id(), message=msg))
        return SENT[-1]

    async def click(self, data):
        msg = Message(
            message_id=self._next_id(),
            date=datetime.datetime.now(),
            chat=self.chat,
            from_user=self.user,
            text="…",
        )
        msg.set_bot(self.bot)
        query = CallbackQuery(
            id=str(self._next_id()),
            from_user=self.user,
            chat_instance="1",
            data=data,
            message=msg,
        )
        query.set_bot(self.bot)
        await self.app.process_update(Update(update_id=self._next_id(), callback_query=query))
        return SENT[-1]


@pytest.fixture()
def harness():
    SENT.clear()
    db.init_db()
    with db.get_conn() as conn:
        for table in ("answers", "questions", "daily_progress", "reading_days",
                      "registrations", "books"):
            conn.execute(f"DELETE FROM {table}")
    h = Harness()
    asyncio.get_event_loop().run_until_complete(h.start())
    return h


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ----------------------------------------------------------- ساخت برنامه --

def test_generate_days_covers_all_pages():
    days = generate_days(jdatetime.date(1403, 6, 21), 30, 115, 55)
    assert len(days) == 4
    assert days[0]["book_page_from"] == 1
    assert days[-1]["book_page_to"] == 115
    assert days[-1]["pdf_page_to"] == 55
    # روزها پشت‌سرهم و بدون همپوشانی
    for prev, nxt in zip(days, days[1:]):
        assert nxt["book_page_from"] == prev["book_page_to"] + 1
        assert nxt["jalali_date"] != prev["jalali_date"]


def test_generate_days_validates_input():
    with pytest.raises(ValueError):
        generate_days(jdatetime.date(1403, 6, 21), 0, 100)
    with pytest.raises(ValueError):
        generate_days(jdatetime.date(1403, 6, 21), 10, 0)


# ------------------------------------------------------------- دیتابیس --

def test_create_update_and_delete_book():
    db.init_db()
    book_id = db.create_book("کتاب", "نویسنده", "توضیح", 115, 55)
    book = db.get_book(book_id)
    assert book["book_pages"] == 115 and book["pdf_pages"] == 55

    db.update_book_field(book_id, "pdf_pages", 60)
    assert db.get_book(book_id)["pdf_pages"] == 60
    with pytest.raises(ValueError):
        db.update_book_field(book_id, "status; DROP TABLE books", 1)

    db.replace_reading_days(book_id, generate_days(jdatetime.date(1403, 6, 21), 30, 115, 60))
    assert len(db.get_reading_days(book_id)) == 4
    # جایگزینی برنامه، روزهای قبلی را پاک می‌کند
    db.replace_reading_days(book_id, generate_days(jdatetime.date(1403, 6, 21), 60, 115, 60))
    assert len(db.get_reading_days(book_id)) == 2

    db.delete_book(book_id)
    assert db.get_book(book_id) is None
    assert db.get_reading_days(book_id) == []


# ------------------------------------------- رفتار لغو و جابه‌جایی دستورات --

def test_cancel_resets_conversation(harness):
    assert "عنوان کتاب" in run(harness.send("➕ کتاب جدید"))
    assert "لغو" in run(harness.send("/cancel"))
    # دستور بعدی نباید به‌عنوان ورودی مسیر قبلی خوانده شود
    assert "نویسنده" not in run(harness.send("📊 گزارش روز"))


def test_menu_button_switches_flow_without_cancel(harness):
    run(harness.send("➕ کتاب جدید"))
    assert "نویسنده" not in run(harness.send("📚 لیست کتاب‌ها"))


def test_full_book_and_schedule_flow(harness):
    run(harness.send("➕ کتاب جدید"))
    run(harness.send("آدمخواران"))
    run(harness.send("ژان تولی"))
    run(harness.send("-"))
    run(harness.send("115"))
    out = run(harness.send("55"))
    assert "ساخته شد" in out

    book = db.list_books()[0]
    assert book["book_pages"] == 115 and book["pdf_pages"] == 55

    run(harness.send("📅 تعیین برنامه همخوانی"))
    out = run(harness.click(f"sched_book:{book['id']}"))
    assert "هنوز برنامه‌ای ثبت نشده" in out

    run(harness.click("sched:auto"))
    run(harness.send("1403/06/21"))
    out = run(harness.send("30"))
    assert "📚 کتاب: صفحه 1 تا 30" in out

    run(harness.click("schedc:save"))
    days = db.get_reading_days(book["id"])
    assert len(days) == 4

    # نمایش برنامه‌ی موجود موقع انتخاب دوباره‌ی کتاب
    run(harness.send("📅 تعیین برنامه همخوانی"))
    out = run(harness.click(f"sched_book:{book['id']}"))
    assert "💻 پی دی اف" in out

    # حذف کتاب
    run(harness.send("🗑 حذف کتاب"))
    run(harness.click(f"del_book:{book['id']}"))
    run(harness.click(f"del_confirm:yes:{book['id']}"))
    assert db.get_book(book["id"]) is None


def test_edit_book_flow(harness):
    book_id = db.create_book("قدیمی", "ن", "", 100, 50)
    run(harness.send("✏️ ویرایش کتاب"))
    run(harness.click(f"edit_book:{book_id}"))
    run(harness.click("edit_field:title"))
    out = run(harness.send("عنوان جدید"))
    assert "به‌روز شد" in out
    assert db.get_book(book_id)["title"] == "عنوان جدید"
