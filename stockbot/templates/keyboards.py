from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("📋 ملخص", callback_data='summary'),
            InlineKeyboardButton("🏢 معلومات الشركة", callback_data='profile')
        ],
        [
            InlineKeyboardButton("📅 بيانات تاريخية", callback_data='historical_data'),
            InlineKeyboardButton("💸 توزيعات الأرباح", callback_data='dividends')
        ],
        [
            InlineKeyboardButton("📊 قوائم مالية", callback_data='financial_data'),
            InlineKeyboardButton("📈 بيانات مالية", callback_data='stats')
        ],
        [
            InlineKeyboardButton("✅ التحقق الشرعي", callback_data='shariah_check'),
            InlineKeyboardButton("ℹ️ تعليمات ومساعدة", callback_data='learn_help')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
