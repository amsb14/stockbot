# stockbot/utils/formatting.py
from datetime import datetime



# def format_huge_numbers(value):
#     try:
#         value = float(value)
#         sign = "-" if value < 0 else ""
#         abs_val = abs(value)
#
#         if abs_val >= 1e12:
#             return f"{sign}{abs_val/1e12:.2f}T"
#         elif abs_val >= 1e9:
#             return f"{sign}{abs_val/1e9:.2f}B"
#         elif abs_val >= 1e6:
#             return f"{sign}{abs_val/1e6:.2f}M"
#         else:
#             return f"{value:,.2f}"
#     except (ValueError, TypeError):
#         return "غير متوفر"


def format_huge_numbers(value):
    try:
        value = float(value)
        sign = "-" if value < 0 else ""
        abs_val = abs(value)

        if abs_val >= 1e12:
            return f"{sign}{abs_val / 1e12:.2f} تريليون"
        elif abs_val >= 1e9:
            return f"{sign}{abs_val / 1e9:.2f} مليار"
        elif abs_val >= 1e6:
            return f"{sign}{abs_val / 1e6:.2f} مليون"
        elif abs_val >= 1e3:
            return f"{sign}{abs_val / 1e3:.2f} ألف"
        else:
            return f"{sign}{abs_val:.2f}"
    except (ValueError, TypeError):
        return "غير متوفر"


def safe_format(value, format_spec=",.2f"):
    if isinstance(value, (int, float)):
        return f"{value:{format_spec}}"
    return str(value)

AR_WEEKDAYS = {
    0: "الاثنين",
    1: "الثلاثاء",
    2: "الأربعاء",
    3: "الخميس",
    4: "الجمعة",
    5: "السبت",
    6: "الأحد",
}
EXCHANGE_AR_MAP = {
    "NASDAQ": "ناسداك",
    "NYSE": "بورصة نيويورك",
    "Tadawul": "تاسي",
    "LSE": "بورصة لندن",
    "TSX": "بورصة تورنتو",
    "HKEX": "هونغ كونغ",
    # Add more as needed
}



def arabic_day_name(dt: datetime) -> str:
    """يحول datetime إلى اسم اليوم بالعربية."""
    return AR_WEEKDAYS[dt.weekday()]

def arabic_exchange_name(eng_name: str) -> str:
    return EXCHANGE_AR_MAP.get(eng_name.strip(), eng_name)