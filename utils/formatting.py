# -*- coding: utf-8 -*-
"""
تولید متن‌های نهایی برای اعلان برنامه همخوانی، گزارش‌ها و ... .
"""
import datetime
from typing import List
import sqlite3


def format_schedule_days(days: List[dict]) -> str:
    lines = []
    for d in days:
        lines.append(f"🗓 {d['jalali_date_human']}")
        lines.append(f"📚 کتاب: صفحه {d['book_page_from']} تا {d['book_page_to']}")
        lines.append(f"💻 پی دی اف : {d['pdf_page_from']} تا {d['pdf_page_to']}")
        lines.append("")
    return "\n".join(lines).strip()


def format_nightly_schedule(book: sqlite3.Row, days: List[dict]) -> str:
    """
    برنامه‌ی شبانه‌ای که هر شب ساعت ۱۲ در تاپیک پیگیری پست می‌شود.
    روزهای قبل از امروز با ✅ علامت‌گذاری می‌شوند.
    days باید خروجی days_with_human باشند (کلید jalali_date_human و gregorian_date).
    """
    today_g = str(datetime.date.today())
    lines = [f"📖 «{book['title']}»", ""]
    for d in days:
        is_past = d["gregorian_date"] < today_g
        date_line = f"🗓 {d['jalali_date_human']}"
        if is_past:
            date_line += " ✅"
        lines.append(date_line)
        lines.append(f"📚 کتاب: صفحه {d['book_page_from']} تا {d['book_page_to']}")
        lines.append(f"💻 پی دی اف : {d['pdf_page_from']} تا {d['pdf_page_to']}")
        lines.append("")
    return "\n".join(lines).strip()


def format_previous_day_report(jalali_date_human: str, rows) -> str:
    """
    گزارش روز قبل:
      - تعداد کل اعضای همخوانی
      - تعداد و لیست کسانی که گزارش داده‌اند
      - تعداد و لیست کسانی که گزارش نداده‌اند
    """
    read_users, not_read_users = [], []
    for r in rows:
        name = (
            r["full_name"]
            or (f"@{r['username']}" if r["username"] else str(r["telegram_id"]))
        )
        if r["status"] == "read":
            read_users.append(name)
        else:
            not_read_users.append(name)

    lines = [f"📊 گزارش روز {jalali_date_human}", ""]
    lines.append(f"👥 تعداد اعضای همخوانی: {len(rows)}")
    lines.append("")
    lines.append(f"✅ تعداد گزارش‌داده: {len(read_users)}")
    for n in read_users:
        lines.append(f"   - {n}")
    if not read_users:
        lines.append("   (هیچ‌کس)")
    lines.append("")
    lines.append(f"❌ تعداد گزارش‌نداده: {len(not_read_users)}")
    for n in not_read_users:
        lines.append(f"   - {n}")
    if not not_read_users:
        lines.append("   (هیچ‌کس)")
    return "\n".join(lines)


def format_book_info(book: sqlite3.Row) -> str:
    lines = [
        f"📖 «{book['title']}»",
        f"✍️ نویسنده: {book['author'] or '—'}",
        f"📄 صفحات کتاب: {book['book_pages'] or '—'}",
        f"💻 صفحات پی‌دی‌اف: {book['pdf_pages'] or '—'}",
    ]
    if book["description"]:
        lines.append(f"📝 {book['description']}")
    return "\n".join(lines)


def format_schedule_announcement(book: sqlite3.Row, days: List[dict]) -> str:
    if not days:
        return "هنوز روزی برای این کتاب ثبت نشده."

    first_day = days[0]["jalali_date_human"]
    last_day = days[-1]["jalali_date_human"]

    lines = [
        f"📖✨ هم‌خوانی کتاب «{book['title']}» اثر {book['author']} ✨📖",
        "",
        f"🌤 از {first_day}، همراه با این کتاب همراه شویم :)",
        "",
    ]
    lines.append(format_schedule_days(days))
    lines.append("")
    lines.append(f"🌵 پایان سفر: {last_day}")
    return "\n".join(lines)


def format_daily_report_line(
    full_name: str, user_identifier: str, jalali_date_human: str, read: bool
) -> str:
    mark = "✅" if read else "❌"
    verb = "این بخش رو خوند" if read else "هنوز این بخش رو نخونده"
    return f"{jalali_date_human} - {full_name} | {user_identifier} {verb}.{mark}"


def format_day_report(jalali_date_human: str, rows: List[sqlite3.Row]) -> str:
    """
    فقط دو بخش:
    - خوانده‌اند (status == 'read')
    - نخوانده‌اند (status == 'pending' یا 'not_read' یا هر چیز دیگر)
    """
    read_list, not_read_list = [], []
    for r in rows:
        name = (
            r["full_name"]
            or (f"@{r['username']}" if r["username"] else str(r["telegram_id"]))
        )
        if r["status"] == "read":
            read_list.append(name)
        else:
            not_read_list.append(name)

    lines = [f"📊 گزارش روز {jalali_date_human}", ""]
    lines.append(f"✅ خوانده‌اند ({len(read_list)}):")
    lines += [f"  - {n}" for n in read_list] or ["  (هیچکس)"]
    lines.append("")
    lines.append(f"❌ نخوانده‌اند ({len(not_read_list)}):")
    lines += [f"  - {n}" for n in not_read_list] or ["  (هیچکس)"]
    return "\n".join(lines)


def format_answers_report(book_title: str, report_data: list) -> str:
    """
    گزارش کامل جواب افراد به سوالات یک کتاب:
    - به ازای هر نفر نشان می‌دهد به کدام سوالات پاسخ داده
    - در انتها لیست کسانی که هیچ پاسخی نداده‌اند
    """
    lines = [f"📝 گزارش جواب افراد — «{book_title}»", ""]

    no_answer_users = []

    for item in report_data:
        user = item["user"]
        name = user["full_name"] or (f"@{user['username']}" if user["username"] else str(user["telegram_id"]))
        username_part = f" | @{user['username']}" if user["username"] else ""

        total = len(item["questions"])
        answered = item["total_answered"]

        if answered == 0:
            no_answer_users.append(name + username_part)
            continue

        submitted_mark = " ✅ (ارسال نهایی)" if item["submitted"] else ""
        lines.append(f"👤 {name}{username_part}{submitted_mark}")
        lines.append(f"   پاسخ‌داده: {answered} از {total} سوال")

        for q in item["questions"]:
            has_ans = item["answers"].get(q["id"], False)
            mark = "✅ جواب داده" if has_ans else "❌ جواب نداده"
            lines.append(f"   سوال {q['order_index']}: {mark}")

        lines.append("")

    if no_answer_users:
        lines.append("─" * 30)
        lines.append(f"🚫 شرکت‌کرده‌ولی‌جواب‌نداده ({len(no_answer_users)} نفر):")
        for n in no_answer_users:
            lines.append(f"   - {n}")

    return "\n".join(lines)


def format_members_list(book_title: str, members: list) -> str:
    """
    پیام لیست اعضای ثبت‌نام‌کرده در یک کتاب.
    این پیام هر بار که عضو جدیدی اضافه می‌شود به‌روز می‌شود.
    """
    lines = [
        f"👥 اعضای همخوانی «{book_title}»",
        f"تعداد: {len(members)} نفر",
        "",
    ]
    for i, m in enumerate(members, start=1):
        name = m["full_name"] or (f"@{m['username']}" if m["username"] else "کاربر")
        username_part = f" | @{m['username']}" if m["username"] else ""
        lines.append(f"{i}. {name}{username_part}")
    if not members:
        lines.append("(هنوز کسی ثبت‌نام نکرده)")
    return "\n".join(lines)


def format_answer_submitted_notification(
    book_title: str,
    user_full_name: str,
    username: str | None,
    answered_count: int,
    total_count: int,
) -> str:
    """
    پیامی که وقتی کاربر پاسخ‌هایش را ثبت نهایی کرد در گروه اعلام می‌شود.
    شامل نام، آیدی و تعداد سوالات پاسخ‌داده‌شده از کل.
    """
    name_part = user_full_name or (f"@{username}" if username else "یک عضو")
    username_part = f" | @{username}" if username else ""
    count_part = (
        f"{answered_count} از {total_count} سوال"
        if answered_count < total_count
        else f"همه {total_count} سوال"
    )
    return (
        f"📬 {name_part}{username_part}\n"
        f"به {count_part} کتاب «{book_title}» پاسخ داد! 🎉"
    )


def format_question_report(question_text: str, answers: List[sqlite3.Row]) -> str:
    lines = [f"❓ {question_text}", ""]
    for i, a in enumerate(answers, start=1):
        name = a["full_name"] or (f"@{a['username']}" if a["username"] else "کاربر")
        lines.append(f"{i} - {name}")
        lines.append(a["text"])
        lines.append("")
    if not answers:
        lines.append("(هنوز کسی پاسخ نداده است)")
    return "\n".join(lines)