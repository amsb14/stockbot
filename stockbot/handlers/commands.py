import logging
from datetime import date
from telegram import Update
from telegram.ext import CallbackContext
from stockbot.database.connection import get_db_conn, put_db_conn
from stockbot.database.queries import (
    SUBSCRIBER_SELECT,
    SUBSCRIBER_UPDATE_PROFILE,
    SUBSCRIBER_UPDATE_FREE,
    SUBSCRIBER_INSERT,
)
from stockbot.handlers.base import with_subscription_check
from stockbot.handlers.texts import (
    LEARN_TEMPLATE
)
from stockbot.templates.keyboards import get_main_keyboard

@with_subscription_check
def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id
    today = date.today()

    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(SUBSCRIBER_SELECT, (chat_id,))
            row = cur.fetchone()

            if row:
                sub_type, expires_at, last_reset = row

                if sub_type == 'premium' and expires_at and expires_at >= today:
                    cur.execute(
                        SUBSCRIBER_UPDATE_PROFILE,
                        (user.first_name, user.username, user.language_code, chat_id)
                    )
                    conn.commit()
                    update.message.reply_text(
                        f"👋 مرحباً مرةً أخرى! اشتراكك المميز صالح حتى {expires_at}."
                    )
                    return

                reset_usage = (last_reset is None) or (last_reset < today)

                cur.execute(
                    SUBSCRIBER_UPDATE_FREE,
                    (
                        user.first_name,
                        user.username,
                        user.language_code,
                        reset_usage,
                        reset_usage,
                        today,
                        chat_id,
                    )
                )
                conn.commit()

            else:
                cur.execute(
                    SUBSCRIBER_INSERT,
                    (
                        chat_id,
                        user.first_name,
                        user.username,
                        user.language_code,
                        today,
                    )
                )
                conn.commit()

    finally:
        put_db_conn(conn)

    update.message.reply_text(
        "👋 Welcome to StockBot!\n\n"
        "You have been registered as a Free user.\n"
        "You can use up to 5 advanced‐feature requests per day."
    )

@with_subscription_check
def status(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id

    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT subscription_type, usage_count, usage_limit, expires_at, is_active
                FROM subscribers
                WHERE chat_id = %s
                """,
                (chat_id,)
            )
            result = cur.fetchone()

            if not result:
                update.message.reply_text("❌ You are not registered. Please send /start to begin.")
                return

            subscription_type, usage_count, usage_limit, expires_at, is_active = result

            if not is_active:
                update.message.reply_text("⚠️ Your subscription is inactive.\nSend /start to re-activate your access.")
                return

            if subscription_type == 'premium':
                exp_text = (
                    f"🗓️ Expiration Date: {expires_at.strftime('%Y-%m-%d')}"
                    if expires_at else "∞ No expiry set"
                )
                msg = (
                    "⭐ You are a **Premium User**\n"
                    f"{exp_text}\n"
                    "✅ Full access is enabled."
                )
            else:
                msg = (
                    "👤 You are a **Free User**\n"
                    f"📊 Usage today: {usage_count}/{usage_limit}\n"
                    "⚠️ Upgrade to premium for unlimited access."
                )

            update.message.reply_text(msg, parse_mode='Markdown')

    finally:
        put_db_conn(conn)

def grant_premium(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("Usage: /grant_premium <chat_id>")
        return

    try:
        chat_id = int(context.args[0])
    except ValueError:
        update.message.reply_text("Invalid chat_id.")
        return

    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE subscribers
                SET subscription_type = 'premium',
                    usage_limit = NULL,
                    usage_count = 0,
                    expires_at = CURRENT_DATE + INTERVAL '30 days'
                WHERE chat_id = %s
            """, (chat_id,))
            conn.commit()
    finally:
        put_db_conn(conn)

    update.message.reply_text(f"✅ User {chat_id} upgraded to Premium for 30 days.")

def help_command(update, context):
    update.message.reply_text(
        text=LEARN_TEMPLATE,
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )
