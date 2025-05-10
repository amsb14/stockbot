from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from stockbot.services.ticker_service import parse_symbol, symbol_exists_in_db, find_top_matches
from stockbot.handlers.base import with_subscription_check
from stockbot.templates.keyboards import get_main_keyboard

@with_subscription_check
def handle_message(update, context):
    raw_input = update.message.text.strip()
    if raw_input.startswith("/"):
        raw_input = raw_input[1:].strip()

    # Map Arabic-Indic digits to English digits
    arabic_digits = "٠١٢٣٤٥٦٧٨٩"
    english_digits = "0123456789"
    trans_table = str.maketrans(arabic_digits, english_digits)
    raw_input = raw_input.translate(trans_table)

    db_symbol, api_symbol, is_saudi = parse_symbol(raw_input)
    if symbol_exists_in_db(db_symbol):
        context.user_data.update({
            "db_symbol": db_symbol,
            "api_symbol": api_symbol,
            "is_saudi": is_saudi
        })
        return update.message.reply_text(
            f"Selected ticker: {db_symbol} ✅\nChoose a service from the menu 👇",
            reply_markup=get_main_keyboard()
        )

    matches = find_top_matches(raw_input)
    if matches:
        buttons = [
            [InlineKeyboardButton(f"{name} ({sym})", callback_data=f"select_{sym}")]
            for sym, name, _ in matches
        ]
        return update.message.reply_text(
            "Did you mean one of the following?",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    update.message.reply_text(
        f"❌ Could not find any ticker matching '{raw_input}'. Try a more precise symbol or name (e.g. AAPL or 2222)."
    )
