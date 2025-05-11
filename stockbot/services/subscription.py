import logging
from datetime import date
from stockbot.database.connection import get_db_conn, put_db_conn
from stockbot.database.queries import SUBSCRIBER_CONSUME_FREE_CREDIT, SUBSCRIBER_SELECT_USAGE
from stockbot.database.queries import SUBSCRIBER_RESET_DAILY_USAGE

def consume_free_credit(chat_id: int) -> bool:
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(SUBSCRIBER_CONSUME_FREE_CREDIT, (chat_id,))
            row = cur.fetchone()
            if not row:
                return False
            conn.commit()
            return True
    finally:
        put_db_conn(conn)

def check_usage_quota_for_query(query, chat_id) -> bool:
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(SUBSCRIBER_SELECT_USAGE, (chat_id,))
            row = cur.fetchone()
    finally:
        put_db_conn(conn)

    if row and row[0] == 'free':
        if not consume_free_credit(chat_id):
            query.answer(
                "شكرا لك على استخدامك بوت نمو+! نود اشعارك بإنتهاء الحد اليومي للإستخدام .",
                show_alert=True
            )
            return False
    return True

def reset_daily_usage():
    """
    Reset free users' daily usage_count to zero.
    Should be called once per day (00:00 Asia/Riyadh).
    """
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(SUBSCRIBER_RESET_DAILY_USAGE, (date.today(),))
            conn.commit()
        logging.info("🔄 reset_daily_usage: freed up usage_count for all free subscribers")
    except Exception as e:
        logging.error(f"reset_daily_usage failed: {e}", exc_info=True)
    finally:
        put_db_conn(conn)