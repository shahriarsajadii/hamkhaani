# -*- coding: utf-8 -*-
"""
ساخت خودکار برنامه همخوانی بر اساس تاریخ شروع، تعداد صفحه در روز و تعداد کل صفحات کتاب.

صفحات پی‌دی‌اف به نسبت تعداد کل صفحات پی‌دی‌اف به تعداد کل صفحات کتاب نگاشت می‌شوند،
بنابراین اگر فایل پی‌دی‌اف صفحه‌شماری متفاوتی داشته باشد باز هم بازه‌ها درست درمی‌آید.
"""
import datetime
from typing import List, Dict, Any, Optional

import jdatetime


def generate_days(start_jdate: jdatetime.date, pages_per_day: int, book_pages: int,
                  pdf_pages: Optional[int] = None) -> List[Dict[str, Any]]:
    if pages_per_day < 1:
        raise ValueError("تعداد صفحه در روز باید حداقل ۱ باشد.")
    if book_pages < 1:
        raise ValueError("تعداد صفحات کتاب باید حداقل ۱ باشد.")

    total_pdf = pdf_pages or book_pages
    ratio = total_pdf / book_pages

    days: List[Dict[str, Any]] = []
    page_from = 1
    day_date = start_jdate
    while page_from <= book_pages:
        page_to = min(page_from + pages_per_day - 1, book_pages)
        pdf_from = min(total_pdf, int(round((page_from - 1) * ratio)) + 1)
        pdf_to = min(total_pdf, max(pdf_from, int(round(page_to * ratio))))
        days.append(
            {
                "jalali_date": day_date.strftime("%Y/%m/%d"),
                "gregorian_date": day_date.togregorian().isoformat(),
                "book_page_from": page_from,
                "book_page_to": page_to,
                "pdf_page_from": pdf_from,
                "pdf_page_to": pdf_to,
            }
        )
        page_from = page_to + 1
        day_date = day_date + datetime.timedelta(days=1)

    return days
