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
    book_pages INTEGER,
    pdf_pages INTEGER,
    group_chat_id INTEGER,
    topic_pigiri_id INTEGER,
    status TEXT DEFAULT 'draft'
        CHECK(status IN ('draft', 'active', 'finished')),
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reading_days (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    day_index INTEGER NOT NULL,
    jalali_date TEXT NOT NULL,
    gregorian_date TEXT NOT NULL,
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
    FOREIGN KEY(book_id) REFERENCES books(id)
);

CREATE TABLE IF NOT EXISTS daily_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reading_day_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    status TEXT DEFAULT 'pending'
        CHECK(status IN ('pending', 'read', 'not_read')),
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

CREATE TABLE IF NOT EXISTS answer_submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    submitted_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(book_id, user_id),
    FOREIGN KEY(book_id) REFERENCES books(id),
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
        _migrate(conn)


def _migrate(conn: sqlite3.Connection):
    """ستون‌های جدید را به دیتابیس‌های قدیمی اضافه می‌کند."""
    columns = {r["name"] for r in conn.execute("PRAGMA table_info(books)").fetchall()}
    for column in ("book_pages", "pdf_pages"):
        if column not in columns:
            conn.execute(f"ALTER TABLE books ADD COLUMN {column} INTEGER")


# ---------------------------------------------------------------- users ----

def upsert_user(telegram_id: int, username: Optional[str], full_name: str) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM users WHERE telegram_id=?", (telegram_id,)
        ).fetchone()
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

def create_book(
    title: str,
    author: str,
    description: str,
    book_pages: Optional[int] = None,
    pdf_pages: Optional[int] = None,
) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO books
               (title, author, description, book_pages, pdf_pages, status)
               VALUES (?,?,?,?,?, 'draft')""",
            (title, author, description, book_pages, pdf_pages),
        )
        return cur.lastrowid


EDITABLE_BOOK_FIELDS = ("title", "author", "description", "book_pages", "pdf_pages")


def update_book_field(book_id: int, field: str, value):
    if field not in EDITABLE_BOOK_FIELDS:
        raise ValueError(f"فیلد غیرمجاز: {field}")
    with get_conn() as conn:
        conn.execute(f"UPDATE books SET {field}=? WHERE id=?", (value, book_id))


def delete_book(book_id: int):
    """کتاب و تمام داده‌های وابسته به آن (روزها، ثبت‌نام‌ها، سوالات، پاسخ‌ها) را پاک می‌کند."""
    with get_conn() as conn:
        conn.execute(
            """DELETE FROM answers WHERE question_id IN
               (SELECT id FROM questions WHERE book_id=?)""",
            (book_id,),
        )
        conn.execute("DELETE FROM questions WHERE book_id=?", (book_id,))
        conn.execute(
            """DELETE FROM daily_progress WHERE reading_day_id IN
               (SELECT id FROM reading_days WHERE book_id=?)""",
            (book_id,),
        )
        conn.execute("DELETE FROM reading_days WHERE book_id=?", (book_id,))
        conn.execute("DELETE FROM registrations WHERE book_id=?", (book_id,))
        conn.execute("DELETE FROM answer_submissions WHERE book_id=?", (book_id,))
        conn.execute("DELETE FROM books WHERE id=?", (book_id,))


def set_book_topic(book_id: int, group_chat_id: int, thread_id: Optional[int]):
    with get_conn() as conn:
        conn.execute(
            "UPDATE books SET group_chat_id=?, topic_pigiri_id=? WHERE id=?",
            (group_chat_id, thread_id, book_id),
        )


def set_book_status(book_id: int, status: str):
    if status not in {"draft", "active", "finished"}:
        raise ValueError("وضعیت کتاب نامعتبر است.")
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

def add_reading_day(
    book_id: int,
    day_index: int,
    jalali_date: str,
    gregorian_date: str,
    book_from: int,
    book_to: int,
    pdf_from: int,
    pdf_to: int,
) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO reading_days
               (book_id, day_index, jalali_date, gregorian_date,
                book_page_from, book_page_to, pdf_page_from, pdf_page_to)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                book_id,
                day_index,
                jalali_date,
                gregorian_date,
                book_from,
                book_to,
                pdf_from,
                pdf_to,
            ),
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


def replace_reading_days(book_id: int, days: List[Dict[str, Any]]):
    """برنامه قبلی کتاب را پاک و برنامه جدید را جایگزین می‌کند."""
    with get_conn() as conn:
        conn.execute(
            """DELETE FROM daily_progress WHERE reading_day_id IN
               (SELECT id FROM reading_days WHERE book_id=?)""",
            (book_id,),
        )
        conn.execute("DELETE FROM reading_days WHERE book_id=?", (book_id,))
        for idx, d in enumerate(days, start=1):
            conn.execute(
                """INSERT INTO reading_days
                   (book_id, day_index, jalali_date, gregorian_date,
                    book_page_from, book_page_to, pdf_page_from, pdf_page_to)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (
                    book_id,
                    idx,
                    d["jalali_date"],
                    d["gregorian_date"],
                    d["book_page_from"],
                    d["book_page_to"],
                    d["pdf_page_from"],
                    d["pdf_page_to"],
                ),
            )


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
                   WHERE r.user_id=? AND b.status=?
                   ORDER BY b.id DESC""",
                (user_id, status),
            ).fetchall()

        return conn.execute(
            """SELECT b.* FROM books b
               JOIN registrations r ON r.book_id = b.id
               WHERE r.user_id=?
               ORDER BY b.id DESC""",
            (user_id,),
        ).fetchall()


# ------------------------------------------------------- daily progress ----

def ensure_progress_rows(reading_day_id: int, book_id: int):
    """برای همه کاربران ثبت‌نام‌کرده در این کتاب، یک ردیف pending می‌سازد."""
    with get_conn() as conn:
        users = conn.execute(
            "SELECT user_id FROM registrations WHERE book_id=?", (book_id,)
        ).fetchall()
        for user in users:
            conn.execute(
                """INSERT OR IGNORE INTO daily_progress
                   (reading_day_id, user_id, status)
                   VALUES (?, ?, 'pending')""",
                (reading_day_id, user["user_id"]),
            )


def get_progress_for_user(reading_day_id: int, user_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            """SELECT * FROM daily_progress
               WHERE reading_day_id=? AND user_id=?""",
            (reading_day_id, user_id),
        ).fetchone()


def set_progress(reading_day_id: int, user_id: int, status: str) -> bool:
    """
    گزارش روزانه را فقط یک‌بار ثبت می‌کند.

    True  -> گزارش جدید ثبت شد.
    False -> قبلاً برای همین روز گزارشی ثبت شده و قابل تغییر نیست.
    """
    if status not in {"read", "not_read"}:
        raise ValueError("وضعیت گزارش نامعتبر است.")

    now = datetime.datetime.now().isoformat(timespec="seconds")
    with get_conn() as conn:
        cur = conn.execute(
            """UPDATE daily_progress
               SET status=?, reported_at=?
               WHERE reading_day_id=? AND user_id=? AND status='pending'""",
            (status, now, reading_day_id, user_id),
        )
        if cur.rowcount == 1:
            return True

        cur = conn.execute(
            """INSERT INTO daily_progress
               (reading_day_id, user_id, status, reported_at)
               SELECT ?, ?, ?, ?
               WHERE NOT EXISTS (
                   SELECT 1 FROM daily_progress
                   WHERE reading_day_id=? AND user_id=?
               )""",
            (reading_day_id, user_id, status, now, reading_day_id, user_id),
        )
        return cur.rowcount == 1


def get_progress_for_day(reading_day_id: int) -> List[sqlite3.Row]:
    """
    همه ثبت‌نامی‌های کتاب را برمی‌گرداند؛ حتی اگر هنوز رکورد daily_progress
    برایشان ساخته نشده باشد، در این حالت status برابر pending است.
    """
    with get_conn() as conn:
        return conn.execute(
            """SELECT
                   COALESCE(dp.id, -1) AS id,
                   rd.id AS reading_day_id,
                   u.id AS user_id,
                   COALESCE(dp.status, 'pending') AS status,
                   dp.reported_at,
                   u.full_name,
                   u.username,
                   u.telegram_id
               FROM reading_days rd
               JOIN registrations reg
                 ON reg.book_id = rd.book_id
               JOIN users u
                 ON u.id = reg.user_id
               LEFT JOIN daily_progress dp
                 ON dp.reading_day_id = rd.id
                AND dp.user_id = u.id
               WHERE rd.id=?
               ORDER BY u.id""",
            (reading_day_id,),
        ).fetchall()


def get_user_book_progress(user_id: int, book_id: int) -> List[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            """SELECT
                   rd.id AS reading_day_id,
                   rd.day_index,
                   rd.jalali_date,
                   rd.gregorian_date,
                   rd.book_page_from,
                   rd.book_page_to,
                   rd.pdf_page_from,
                   rd.pdf_page_to,
                   COALESCE(dp.status, 'pending') AS status,
                   dp.reported_at
               FROM reading_days rd
               LEFT JOIN daily_progress dp
                 ON dp.reading_day_id = rd.id
                AND dp.user_id = ?
               WHERE rd.book_id=?
               ORDER BY rd.day_index""",
            (user_id, book_id),
        ).fetchall()


def can_user_answer_book(user_id: int, book_id: int) -> bool:
    """
    کاربر فقط وقتی می‌تواند سوالات را ببیند که:
      - در کتاب ثبت‌نام کرده باشد.
      - برای همه روزهای برنامه گزارش ثبت شده باشد.
      - همه گزارش‌ها وضعیت read داشته باشند.
    """
    with get_conn() as conn:
        registered = conn.execute(
            "SELECT 1 FROM registrations WHERE book_id=? AND user_id=?",
            (book_id, user_id),
        ).fetchone()
        if not registered:
            return False

        total_days = conn.execute(
            "SELECT COUNT(*) AS count FROM reading_days WHERE book_id=?",
            (book_id,),
        ).fetchone()["count"]

        if total_days == 0:
            return False

        unread_or_unreported = conn.execute(
            """SELECT COUNT(*) AS count
               FROM reading_days rd
               LEFT JOIN daily_progress dp
                 ON dp.reading_day_id = rd.id
                AND dp.user_id = ?
               WHERE rd.book_id=?
                 AND COALESCE(dp.status, 'pending') <> 'read'""",
            (user_id, book_id),
        ).fetchone()["count"]

        return unread_or_unreported == 0


def get_pending_progress_for_user(
    user_id: int, reading_day_id: int
) -> Optional[sqlite3.Row]:
    return get_progress_for_user(reading_day_id, user_id)


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
            "SELECT * FROM questions WHERE book_id=? ORDER BY order_index, id",
            (book_id,),
        ).fetchall()


def get_question(question_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM questions WHERE id=?", (question_id,)
        ).fetchone()


def update_question(question_id: int, text: str):
    text = text.strip()
    if not text:
        raise ValueError("متن سوال نمی‌تواند خالی باشد.")
    with get_conn() as conn:
        conn.execute(
            "UPDATE questions SET text=? WHERE id=?", (text, question_id)
        )


def delete_question(question_id: int):
    """
    پاسخ‌های وابسته هم حذف می‌شوند تا به خاطر Foreign Key حذف سوال شکست نخورد.
    """
    with get_conn() as conn:
        conn.execute("DELETE FROM answers WHERE question_id=?", (question_id,))
        conn.execute("DELETE FROM questions WHERE id=?", (question_id,))


# ----------------------------------------------------------------- answers -

def save_answer(question_id: int, user_id: int, text: str):
    text = (text or "").strip()
    if not text:
        raise ValueError("متن پاسخ نمی‌تواند خالی باشد.")

    with get_conn() as conn:
        # اگر کاربر قبلاً پاسخ‌های این کتاب را ثبت نهایی کرده باشد، اجازه ویرایش نیست.
        q = conn.execute(
            "SELECT book_id FROM questions WHERE id=?", (question_id,)
        ).fetchone()
        if q:
            submitted = conn.execute(
                "SELECT 1 FROM answer_submissions WHERE user_id=? AND book_id=?",
                (user_id, q["book_id"]),
            ).fetchone()
            if submitted:
                raise ValueError("پاسخ‌ها قبلاً ثبت نهایی شده‌اند و قابل ویرایش نیستند.")

        conn.execute(
            """INSERT INTO answers (question_id, user_id, text)
               VALUES (?,?,?)
               ON CONFLICT(question_id, user_id)
               DO UPDATE SET text=excluded.text,
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
            """SELECT a.*, u.full_name, u.username, u.telegram_id
               FROM answers a
               JOIN users u ON u.id = a.user_id
               WHERE a.question_id=?
               ORDER BY a.answered_at""",
            (question_id,),
        ).fetchall()


def get_user_answers_for_book(user_id: int, book_id: int) -> List[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            """SELECT a.* FROM answers a
               JOIN questions q ON q.id = a.question_id
               WHERE q.book_id=? AND a.user_id=?
               ORDER BY q.order_index""",
            (book_id, user_id),
        ).fetchall()


def get_user_answer_for_question(
    user_id: int, question_id: int
) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM answers WHERE user_id=? AND question_id=?",
            (user_id, question_id),
        ).fetchone()


# -------------------------------------------------------- answer submission --

def submit_answers(user_id: int, book_id: int) -> bool:
    """پاسخ‌های کاربر را برای یک کتاب ثبت نهایی می‌کند (فقط یک‌بار)."""
    with get_conn() as conn:
        try:
            conn.execute(
                "INSERT INTO answer_submissions (user_id, book_id) VALUES (?,?)",
                (user_id, book_id),
            )
            return True
        except sqlite3.IntegrityError:
            return False


def is_answers_submitted(user_id: int, book_id: int) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM answer_submissions WHERE user_id=? AND book_id=?",
            (user_id, book_id),
        ).fetchone()
        return row is not None

# ------------------------------------------------- members progress list ---

def get_book_members_progress(book_id: int) -> List[sqlite3.Row]:
    """
    لیست همه اعضای یک کتاب به همراه تعداد روزهایی که گزارش «خوندم» داده‌اند.
    برای نمایش عمومی در هر دو پنل ادمین و کاربر استفاده می‌شود.
    """
    with get_conn() as conn:
        return conn.execute(
            """SELECT
                   u.full_name,
                   u.username,
                   u.telegram_id,
                   COUNT(dp.id) AS read_days
               FROM registrations reg
               JOIN users u ON u.id = reg.user_id
               LEFT JOIN daily_progress dp
                 ON dp.user_id = u.id
                AND dp.status = 'read'
                AND dp.reading_day_id IN (
                    SELECT id FROM reading_days WHERE book_id = ?
                )
               WHERE reg.book_id = ?
               GROUP BY u.id
               ORDER BY read_days DESC, u.full_name""",
            (book_id, book_id),
        ).fetchall()


def get_previous_reading_day_index(book_id: int, day_index: int) -> Optional[int]:
    """ایندکس روز قبل از day_index را برمی‌گرداند، یا None اگر اول باشد."""
    if day_index <= 1:
        return None
    return day_index - 1


def get_book_answers_report(book_id: int):
    """
    گزارش کامل پاسخ‌های اعضا برای یک کتاب:
    - چه کسانی به کدام سوالات پاسخ داده‌اند
    - چه کسانی هیچ سوالی پاسخ نداده‌اند (ثبت‌نام کرده ولی جواب صفر)
    """
    with get_conn() as conn:
        questions = conn.execute(
            "SELECT * FROM questions WHERE book_id=? ORDER BY order_index, id",
            (book_id,),
        ).fetchall()

        members = conn.execute(
            """SELECT u.* FROM users u
               JOIN registrations r ON r.user_id = u.id
               WHERE r.book_id=?
               ORDER BY u.full_name""",
            (book_id,),
        ).fetchall()

        result = []
        for user in members:
            user_answers = {}
            for q in questions:
                ans = conn.execute(
                    "SELECT * FROM answers WHERE question_id=? AND user_id=?",
                    (q["id"], user["id"]),
                ).fetchone()
                user_answers[q["id"]] = ans is not None

            submitted = conn.execute(
                "SELECT 1 FROM answer_submissions WHERE user_id=? AND book_id=?",
                (user["id"], book_id),
            ).fetchone()

            result.append({
                "user": user,
                "questions": questions,
                "answers": user_answers,
                "submitted": submitted is not None,
                "total_answered": sum(1 for v in user_answers.values() if v),
            })

        return result


def is_previous_day_reported(book_id: int, user_id: int, day_index: int) -> bool:
    """
    بررسی می‌کند آیا کاربر روز قبل را گزارش داده یا نه.
    اگر day_index == 1 باشد (اولین روز)، همیشه True برمی‌گرداند.
    """
    if day_index <= 1:
        return True
    with get_conn() as conn:
        row = conn.execute(
            """SELECT dp.status
               FROM reading_days rd
               LEFT JOIN daily_progress dp
                 ON dp.reading_day_id = rd.id
                AND dp.user_id = ?
               WHERE rd.book_id = ? AND rd.day_index = ?""",
            (user_id, book_id, day_index - 1),
        ).fetchone()
        if row is None:
            return False
        return row["status"] == "read"