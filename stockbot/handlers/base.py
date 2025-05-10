from functools import wraps
from datetime import date
from stockbot.database.connection import get_db_conn, put_db_conn
from stockbot.database.queries import SUBSCRIBER_SELECT, SUBSCRIBER_UPDATE_FREE
from dateutil.relativedelta import relativedelta


def start_activation(update, context):
    update.message.reply_text(
        "🔑 من فضلك أرسل لي كود التفعيل (مثال: RT45-623S-GTUI).\n"
        "لإلغاء، أرسل /cancel."
    )
    return 1

def handle_activation_code(update, context):
    code = update.message.text.strip()
    chat_id = update.effective_chat.id
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT is_used, expires_at FROM premium_keys WHERE key_code=%s",
                (code,)
            )
            row = cur.fetchone()

            if not row:
                update.message.reply_text("❌ هذا الكود غير معروف.")
            else:
                is_used, expires_at = row
                today = date.today()
                if is_used or (expires_at and expires_at < today):
                    update.message.reply_text("⚠️ الكود مستخدم أو انتهت صلاحيته.")
                else:
                    cur.execute("""
                        UPDATE premium_keys
                           SET is_used = TRUE,
                               used_by_chat = %s,
                               used_at = NOW()
                         WHERE key_code = %s
                    """, (chat_id, code))

                    new_expiry = today + relativedelta(days=30)
                    cur.execute("""
                        INSERT INTO subscribers(chat_id, subscription_type, expires_at)
                        VALUES (%s, 'premium', %s)
                        ON CONFLICT (chat_id) DO UPDATE
                          SET subscription_type = 'premium',
                              expires_at = %s
                    """, (chat_id, new_expiry, new_expiry))

                    update.message.reply_text(
                        f"✅ تم تفعيل بريميوم حتى {new_expiry.isoformat()}!"
                    )
        conn.commit()
    finally:
        put_db_conn(conn)

    return -1

def cancel_activation(update, context):
    update.message.reply_text("🚫 تم إلغاء التفعيل.")
    return -1

def with_subscription_check(fn):
    @wraps(fn)
    def wrapped(update, context, *args, **kwargs):
        cid = update.effective_chat.id
        downgrade_expired(cid)
        return fn(update, context, *args, **kwargs)

    return wrapped

def downgrade_expired(chat_id: int) -> None:
    """
    If the user’s expires_at is in the past but they’re still marked
    as premium, immediately flip them back to free.
    """
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT subscription_type, expires_at
                  FROM subscribers
                 WHERE chat_id = %s
                """,
                (chat_id,),
            )
            row = cur.fetchone()
            if row:
                sub_type, expires_at = row
                if sub_type == "premium" and expires_at and expires_at < date.today():
                    cur.execute(
                        """
                        UPDATE subscribers
                           SET subscription_type = 'free',
                               expires_at        = NULL
                         WHERE chat_id = %s
                        """,
                        (chat_id,),
                    )
                    conn.commit()
    finally:
        put_db_conn(conn)
