# -*- coding: utf-8 -*-
"""
لایه دیتابیس (sqlite3 خام، بدون ORM سنگین، برای سادگی و سبک بودن).
تمام کوئری‌ها اینجا متمرکز شده تا بقیه کد فقط با توابع این ماژول کار کند.
"""
import sqlite3
import datetime
from contextlib import contextmanager
from typing import Optional, List, Dict, Any

from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    full_name TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT,
    description TEXT,
    group_chat_id INTEGER,
    topic_pigiri_id INTEGER,   -- تاپیک پیگیری
    topic_boride_id INTEGER,   -- تاپیک بریده‌ها
    topic_gap_id INTEGER,      -- تاپیک گپ
    status TEXT DEFAULT 'draft',  -- draft / active / finished
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reading_days (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    day_index INTEGER NOT NULL,       -- ترتیب روز در برنامه (1,2,3,...)
    jalali_date TEXT NOT NULL,        -- ذخیره خام مثل '1403/06/21'
    gregorian_date TEXT NOT NULL,     -- برای زمان‌بندی، مثل '2024-09-11'
    book_page_from INTEGER,
    book_page_to INTEGER,
    pdf_page_from INTEGER,
    pdf_page_to INTEGER,
    reminder_sent INTEGER DEFAULT 0,
    FOREIGN KEY(book_id) REFERENCES books(id)
);

CREATE TABLE IF NOT EXISTS registrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    registered_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(book_id, user_id),
    FOREIGN KEY(book_id) REFERENCES books(id),
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS daily_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reading_day_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    status TEXT DEFAULT 'pending',   -- pending / read / not_read
    reported_at TEXT,
    UNIQUE(reading_day_id, user_id),
    FOREIGN KEY(reading_day_id) REFERENCES reading_days(id),
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    order_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    FOREIGN KEY(book_id) REFERENCES books(id)
);

CREATE TABLE IF NOT EXISTS answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    answered_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(question_id, user_id),
    FOREIGN KEY(question_id) REFERENCES questions(id),
    FOREIGN KEY(user_id) REFERENCES users(id)
);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


# ---------------------------------------------------------------- users ----

def upsert_user(telegram_id: int, username: Optional[str], full_name: str) -> int:
    with get_conn() as conn:
        cur = conn.execute("SELECT id FROM users WHERE telegram_id=?", (telegram_id,))
        row = cur.fetchone()
        if row:
            conn.execute(
                "UPDATE users SET username=?, full_name=? WHERE telegram_id=?",
                (username, full_name, telegram_id),
            )
            return row["id"]
        cur = conn.execute(
            "INSERT INTO users (telegram_id, username, full_name) VALUES (?,?,?)",
            (telegram_id, username, full_name),
        )
        return cur.lastrowid


def get_user_by_telegram_id(telegram_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE telegram_id=?", (telegram_id,)
        ).fetchone()


def get_user_by_id(user_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()


# ---------------------------------------------------------------- books ----

def create_book(title: str, author: str, description: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO books (title, author, description, status) VALUES (?,?,?, 'draft')",
            (title, author, description),
        )
        return cur.lastrowid


_TOPIC_COLUMNS = {
    "pigiri": "topic_pigiri_id",
    "boride": "topic_boride_id",
    "gap": "topic_gap_id",
}


def set_book_topic(book_id: int, kind: str, group_chat_id: int, thread_id: int):
    """kind یکی از 'pigiri' / 'boride' / 'gap'."""
    column = _TOPIC_COLUMNS[kind]
    with get_conn() as conn:
        conn.execute(
            f"UPDATE books SET group_chat_id=?, {column}=? WHERE id=?",
            (group_chat_id, thread_id, book_id),
        )


def set_book_status(book_id: int, status: str):
    with get_conn() as conn:
        conn.execute("UPDATE books SET status=? WHERE id=?", (status, book_id))


def get_book(book_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()


def list_books(status: Optional[str] = None) -> List[sqlite3.Row]:
    with get_conn() as conn:
        if status:
            return conn.execute(
                "SELECT * FROM books WHERE status=? ORDER BY id DESC", (status,)
            ).fetchall()
        return conn.execute("SELECT * FROM books ORDER BY id DESC").fetchall()


# --------------------------------------------------------- reading days ----

def add_reading_day(book_id: int, day_index: int, jalali_date: str, gregorian_date: str,
                     book_from: int, book_to: int, pdf_from: int, pdf_to: int) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO reading_days
               (book_id, day_index, jalali_date, gregorian_date,
                book_page_from, book_page_to, pdf_page_from, pdf_page_to)
               VALUES (?,?,?,?,?,?,?,?)""",
            (book_id, day_index, jalali_date, gregorian_date, book_from, book_to, pdf_from, pdf_to),
        )
        return cur.lastrowid


def get_reading_days(book_id: int) -> List[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM reading_days WHERE book_id=? ORDER BY day_index", (book_id,)
        ).fetchall()


def get_reading_day(reading_day_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM reading_days WHERE id=?", (reading_day_id,)
        ).fetchone()


def get_reading_days_by_gregorian_date(gdate: str) -> List[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM reading_days WHERE gregorian_date=?", (gdate,)
        ).fetchall()


def mark_reminder_sent(reading_day_id: int):
    with get_conn() as conn:
        conn.execute(
            "UPDATE reading_days SET reminder_sent=1 WHERE id=?", (reading_day_id,)
        )


# -------------------------------------------------------- registrations ----

def register_user_to_book(book_id: int, user_id: int) -> bool:
    """True اگر ثبت‌نام جدید انجام شد، False اگر قبلاً بوده."""
    with get_conn() as conn:
        try:
            conn.execute(
                "INSERT INTO registrations (book_id, user_id) VALUES (?,?)",
                (book_id, user_id),
            )
            return True
        except sqlite3.IntegrityError:
            return False


def is_user_registered(book_id: int, user_id: int) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM registrations WHERE book_id=? AND user_id=?",
            (book_id, user_id),
        ).fetchone()
        return row is not None


def get_registered_users(book_id: int) -> List[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            """SELECT u.* FROM users u
               JOIN registrations r ON r.user_id = u.id
               WHERE r.book_id=?""",
            (book_id,),
        ).fetchall()


def get_user_books(user_id: int, status: Optional[str] = None) -> List[sqlite3.Row]:
    with get_conn() as conn:
        if status:
            return conn.execute(
                """SELECT b.* FROM books b
                   JOIN registrations r ON r.book_id = b.id
                   WHERE r.user_id=? AND b.status=?""",
                (user_id, status),
            ).fetchall()
        return conn.execute(
            """SELECT b.* FROM books b
               JOIN registrations r ON r.book_id = b.id
               WHERE r.user_id=?""",
            (user_id,),
        ).fetchall()


# ------------------------------------------------------- daily progress ----

def ensure_progress_rows(reading_day_id: int, book_id: int):
    """برای همه کاربران ثبت‌نام‌کرده در این کتاب، یک ردیف pending می‌سازد (اگر نبود)."""
    with get_conn() as conn:
        users = conn.execute(
            "SELECT user_id FROM registrations WHERE book_id=?", (book_id,)
        ).fetchall()
        for u in users:
            conn.execute(
                """INSERT OR IGNORE INTO daily_progress (reading_day_id, user_id, status)
                   VALUES (?, ?, 'pending')""",
                (reading_day_id, u["user_id"]),
            )


def set_progress(reading_day_id: int, user_id: int, status: str):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO daily_progress (reading_day_id, user_id, status, reported_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(reading_day_id, user_id)
               DO UPDATE SET status=excluded.status, reported_at=excluded.reported_at""",
            (reading_day_id, user_id, status, datetime.datetime.now().isoformat()),
        )


def get_progress_for_day(reading_day_id: int) -> List[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            """SELECT dp.*, u.full_name, u.username, u.telegram_id
               FROM daily_progress dp
               JOIN users u ON u.id = dp.user_id
               WHERE dp.reading_day_id=?""",
            (reading_day_id,),
        ).fetchall()


def get_pending_progress_for_user(user_id: int, reading_day_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM daily_progress WHERE reading_day_id=? AND user_id=?",
            (reading_day_id, user_id),
        ).fetchone()


# -------------------------------------------------------------- questions --

def add_question(book_id: int, order_index: int, text: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO questions (book_id, order_index, text) VALUES (?,?,?)",
            (book_id, order_index, text),
        )
        return cur.lastrowid


def get_questions(book_id: int) -> List[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM questions WHERE book_id=? ORDER BY order_index", (book_id,)
        ).fetchall()


def get_question(question_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM questions WHERE id=?", (question_id,)).fetchone()


# ----------------------------------------------------------------- answers -

def save_answer(question_id: int, user_id: int, text: str):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO answers (question_id, user_id, text) VALUES (?,?,?)
               ON CONFLICT(question_id, user_id) DO UPDATE SET text=excluded.text,
               answered_at=CURRENT_TIMESTAMP""",
            (question_id, user_id, text),
        )


def has_answered(question_id: int, user_id: int) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM answers WHERE question_id=? AND user_id=?",
            (question_id, user_id),
        ).fetchone()
        return row is not None


def get_answers_for_question(question_id: int) -> List[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            """SELECT a.*, u.full_name, u.username FROM answers a
               JOIN users u ON u.id = a.user_id
               WHERE a.question_id=? ORDER BY a.answered_at""",
            (question_id,),
        ).fetchall()
