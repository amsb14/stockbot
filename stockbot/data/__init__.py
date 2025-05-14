# stockbot/data/__init__.py
from stockbot.database.connection import get_db_conn, put_db_conn
from psycopg2.extras import RealDictCursor

def _load_companies_from_db():
    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT symbol 
                  FROM tickers_ar_en
                 ORDER BY symbol
            """)
            rows = cur.fetchall()
    finally:
        put_db_conn(conn)
    # adjust the key if your column is named differently (e.g. 'ticker')
    return [r['symbol'] for r in rows]

# at import time we fetch the live list from your DB
COMPANIES = _load_companies_from_db()