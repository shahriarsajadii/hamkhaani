# -*- coding: utf-8 -*-
"""
ساخت خودکار برنامه همخوانی بر اساس تاریخ شروع، تعداد صفحه در روز و تعداد کل صفحات کتاب.

اگر pdf_pages داده شود، صفحات پی‌دی‌اف به نسبت محاسبه می‌شوند.
اگر pdf_pages داده نشود (None یا صفر)، فیلدهای pdf_page_from/to در خروجی None خواهند بود.
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

    has_pdf = bool(pdf_pages)
    ratio = (pdf_pages / book_pages) if has_pdf else None

    days: List[Dict[str, Any]] = []
    page_from = 1
    day_date = start_jdate
    while page_from <= book_pages:
        page_to = min(page_from + pages_per_day - 1, book_pages)

        if has_pdf:
            pdf_from = min(pdf_pages, int(round((page_from - 1) * ratio)) + 1)
            pdf_to = min(pdf_pages, max(pdf_from, int(round(page_to * ratio))))
        else:
            pdf_from = None
            pdf_to = None

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