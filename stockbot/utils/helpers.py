import logging
from stockbot.database.connection import get_db_conn, put_db_conn

def get_arabic_name_from_db(symbol: str) -> str:
    """
    Returns Arabic name for a symbol if found in tickers_ar_en.
    Automatically handles .SR suffix for Saudi stocks.
    """
    conn = get_db_conn()

    # Normalize: add ".SR" if it looks like a Saudi stock (4-digit code)
    if symbol.isdigit() and len(symbol) == 4:
        symbol = f"{symbol}.SR"

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT arabic_name
                FROM tickers_ar_en
                WHERE symbol = %s
                LIMIT 1
            """, (symbol,))
            row = cur.fetchone()
            if row:
                return row[0]
    except Exception as e:
        logging.warning(f"Arabic name lookup failed for {symbol}: {e}")
    finally:
        put_db_conn(conn)

    return None