# -*- coding: utf-8 -*-
"""
تولید متن‌های نهایی برای اعلان برنامه همخوانی، گزارش‌ها و ... .
"""
from typing import List
import sqlite3


def format_schedule_days(days: List[dict]) -> str:
    """
    فقط لیست روزها، بدون سربرگ:

    🗓 21 شهریور
    📚 کتاب: صفحه 1 تا 30
    💻 پی دی اف : 3 تا 15
    """
    lines = []
    for d in days:
        lines.append(f"🗓 {d['jalali_date_human']}")
        lines.append(f"📚 کتاب: صفحه {d['book_page_from']} تا {d['book_page_to']}")
        lines.append(f"💻 پی دی اف : {d['pdf_page_from']} تا {d['pdf_page_to']}")
        lines.append("")
    return "\n".join(lines).strip()


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
    """
    خروجی دقیقاً مطابق فرمتی که کاربر نمونه داده:

    📖✨ هم‌خوانی کتاب «آدمخواران» اثر ژان تولی ✨📖
    🌤 از 21 شهریور، همراه با این کتاب ...
    🗓 21 شهریور
    📚 کتاب: صفحه 1 تا 30
    💻 پی دی اف : 3 تا 15
    ...
    🌵 پایان سفر: 24 شهریور
    """
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


def format_daily_report_line(full_name: str, jalali_date_human: str, read: bool) -> str:
    mark = "✅" if read else "❌"
    verb = "این بخش رو خوند" if read else "هنوز این بخش رو نخونده"
    return f"{jalali_date_human} - {full_name} {verb}.{mark}"


def format_day_report(jalali_date_human: str, rows: List[sqlite3.Row]) -> str:
    read_list, not_read_list, pending_list = [], [], []
    for r in rows:
        name = r["full_name"] or (f"@{r['username']}" if r["username"] else str(r["telegram_id"]))
        if r["status"] == "read":
            read_list.append(name)
        elif r["status"] == "not_read":
            not_read_list.append(name)
        else:
            pending_list.append(name)

    lines = [f"📊 گزارش روز {jalali_date_human}", ""]
    lines.append(f"✅ خوانده‌اند ({len(read_list)}):")
    lines += [f"  - {n}" for n in read_list] or ["  (هیچکس)"]
    lines.append("")
    lines.append(f"❌ نخوانده‌اند ({len(not_read_list)}):")
    lines += [f"  - {n}" for n in not_read_list] or ["  (هیچکس)"]
    if pending_list:
        lines.append("")
        lines.append(f"⏳ هنوز جواب نداده‌اند ({len(pending_list)}):")
        lines += [f"  - {n}" for n in pending_list]
    return "\n".join(lines)


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
