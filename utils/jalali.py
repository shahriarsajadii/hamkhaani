# -*- coding: utf-8 -*-
"""
توابع کمکی برای کار با تاریخ شمسی (جلالی).
ورودی تاریخ از ادمین به فرم "1403/06/21" گرفته می‌شود.
"""
import jdatetime
import datetime

PERSIAN_MONTHS = [
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
]


def parse_jalali(text: str) -> jdatetime.date:
    """
    ورودی مثل '1403/06/21' یا '1403-06-21' را به jdatetime.date تبدیل می‌کند.
    در صورت نامعتبر بودن، ValueError پرتاب می‌شود.
    """
    text = text.strip().replace("-", "/").replace(" ", "")
    parts = text.split("/")
    if len(parts) != 3:
        raise ValueError("فرمت تاریخ باید به شکل 1403/06/21 باشد.")
    year, month, day = (int(p) for p in parts)
    return jdatetime.date(year, month, day)


def to_gregorian(jdate: jdatetime.date) -> datetime.date:
    return jdate.togregorian()


def format_jalali_human(jdate: jdatetime.date) -> str:
    """خروجی مثل '21 شهریور' (بدون سال، برای نمایش در پیام‌ها مطابق درخواست کاربر)."""
    return f"{jdate.day} {PERSIAN_MONTHS[jdate.month - 1]}"


def format_jalali_full(jdate: jdatetime.date) -> str:
    """خروجی مثل '21 شهریور 1403'."""
    return f"{jdate.day} {PERSIAN_MONTHS[jdate.month - 1]} {jdate.year}"


def today_jalali() -> jdatetime.date:
    return jdatetime.date.today()
