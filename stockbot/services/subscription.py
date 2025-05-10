from stockbot.database.connection import get_db_conn, put_db_conn
from stockbot.database.queries import SUBSCRIBER_CONSUME_FREE_CREDIT, SUBSCRIBER_SELECT_USAGE

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
                "🚫 انتهى حدك المجاني اليوم من الميزات المتقدمة.\n🎁 جرّب الاشتراك لطلبات غير محدودة باستخدام /activate",
                show_alert=True
            )
            return False
    return True
