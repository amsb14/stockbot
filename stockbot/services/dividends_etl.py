import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import yfinance as yf
from psycopg2.extras import execute_values

from stockbot.database.connection import get_db_conn, put_db_conn
from stockbot.data import COMPANIES

# ─── Fetch dividends for one symbol ────────────────────────────────
def fetch_dividends_for_symbol(symbol):
    rows = []
    try:
        ticker = yf.Ticker(symbol)
        divs = ticker.dividends

        if divs is None or divs.empty:
            return []

        for dt, amount in divs.items():
            fiscal_year = dt.year
            rows.append((
                symbol,
                dt.date().isoformat(),
                fiscal_year,
                float(amount),
                datetime.utcnow().date()
            ))

    except Exception as e:
        logging.warning(f"Error fetching dividends for {symbol}: {e}")

    return rows

# ─── Parallel fetch for all symbols ────────────────────────────────
def get_dividends(symbols):
    all_rows = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_map = {executor.submit(fetch_dividends_for_symbol, sym): sym for sym in symbols}
        for fut in as_completed(future_map):
            try:
                rows = fut.result()
                all_rows.extend(rows)
            except Exception as e:
                logging.warning(f"Dividends failed for {future_map[fut]}: {e}")
    return all_rows

# ─── Insert into PostgreSQL with deduplication ─────────────────────
def insert_dividends(rows):
    # Deduplicate by (symbol, dividend_date)
    unique = {(r[0], r[1]): r for r in rows}.values()

    sql = """
    INSERT INTO dividends (
        symbol,
        dividend_date,
        fiscal_year,
        amount,
        updated_date
    ) VALUES %s
    ON CONFLICT (symbol, dividend_date) DO UPDATE SET
        amount       = EXCLUDED.amount,
        fiscal_year  = EXCLUDED.fiscal_year,
        updated_date = EXCLUDED.updated_date;
    """

    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            execute_values(cur, sql, list(unique))
        conn.commit()
    except Exception as e:
        conn.rollback()
        logging.error(f"Insert failed: {e}")
    finally:
        put_db_conn(conn)

# ─── Main entry point for refresh command ──────────────────────────
def refresh_dividends_test():
    """
    Fetch & upsert dividends on demand.
    Returns the number of rows processed.
    """
    rows = get_dividends(COMPANIES)
    if not rows:
        return 0
    insert_dividends(rows)
    return len(rows)
