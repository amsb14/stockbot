# stockbot/services/daily_closes_etl.py
import os
import logging
import time
import threading
from datetime import date, datetime, timedelta
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import pytz

from psycopg2.extras import execute_values
from stockbot.database.connection import get_db_conn, put_db_conn
from stockbot.data import COMPANIES
from stockbot.services.api.twelvedata import td_client, td_kwargs

import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="twelvedata.mixins")
warnings.filterwarnings("ignore", category=FutureWarning, module="twelvedata.mixins")

# ─────────── Configuration ───────────
# Date range (defaults to today)
START_DATE_STR = os.getenv("START_DATE")
END_DATE_STR   = os.getenv("END_DATE")
if START_DATE_STR and END_DATE_STR:
    START_DATE = datetime.strptime(START_DATE_STR, "%Y-%m-%d").date()
    END_DATE   = datetime.strptime(END_DATE_STR,   "%Y-%m-%d").date()
else:
    START_DATE = END_DATE = date.today()

# build date list
_date_list = []
_current = START_DATE
while _current <= END_DATE:
    _date_list.append(_current)
    _current += timedelta(days=1)

# ─────────── Rate limiter ───────────
RATE_LIMIT = 600
PERIOD     = 60
_times     = deque()
_lock      = threading.Lock()

def throttle():
    with _lock:
        now = time.time()
        while _times and now - _times[0] > PERIOD:
            _times.popleft()
        if len(_times) >= RATE_LIMIT:
            sleep_secs = PERIOD - (now - _times[0])
            logging.info(f"Rate limit hit, sleeping {sleep_secs:.1f}s")
            time.sleep(sleep_secs)
            now = time.time()
            while _times and now - _times[0] > PERIOD:
                _times.popleft()
        _times.append(now)

# ─────────── Fetch & upsert logic ───────────
def fetch_symbol_data(sym: str, target: date) -> dict:
    throttle()
    # handle Saudi tickers by stripping .SR and marking is_saudi
    is_saudi = sym.upper().endswith(".SR")
    api_symbol = sym.split('.', 1)[0] if is_saudi else sym

    # prepare parameters
    params = {
        "symbol": api_symbol,
        "interval": "1day",
        "outputsize": 500
    }
    # call TwelveData with country flag if needed
    df = td_client.time_series(
        **params,
        **td_kwargs(is_saudi)
    ).as_pandas().reset_index()
    df.columns = [c.lower() for c in df.columns]
    df['datetime'] = pd.to_datetime(df.get('datetime', df.index))
    df = df.sort_values('datetime')

    # select row matching target_date or fallback
    sel = df[df['datetime'].dt.date == target]
    row = sel.iloc[0] if not sel.empty else df.iloc[-1]

    return {
        'symbol':      sym,
        'trade_date':  row['datetime'].date(),
        'open_price':  float(row['open']),
        'high_price':  float(row['high']),
        'low_price':   float(row['low']),
        'close_price': float(row['close']),
        'volume':      int(row['volume']) if 'volume' in row and not pd.isna(row['volume']) else None
    }


def get_tickers():
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT symbol FROM tickers_ar_en ORDER BY symbol")
            return [r[0] for r in cur.fetchall()]
    finally:
        put_db_conn(conn)


def get_existing(target: date):
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT symbol FROM daily_closes WHERE trade_date = %s",
                (target,)
            )
            return {r[0] for r in cur.fetchall()}
    finally:
        put_db_conn(conn)


def insert_daily_closes(rows):
    sql = """
    INSERT INTO daily_closes (
        symbol, trade_date, open_price, high_price,
        low_price, close_price, volume
    ) VALUES %s
    ON CONFLICT (symbol, trade_date) DO UPDATE SET
        open_price   = EXCLUDED.open_price,
        high_price   = EXCLUDED.high_price,
        low_price    = EXCLUDED.low_price,
        close_price  = EXCLUDED.close_price,
        volume       = EXCLUDED.volume;
    """
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            execute_values(cur, sql, rows)
        conn.commit()
    except Exception as e:
        conn.rollback()
        logging.error(f"Insert failed: {e}")
    finally:
        put_db_conn(conn)


def refresh_daily_closes():
    """ETL entry point: fetch & upsert daily_closes for configured dates."""
    total = 0
    all_syms = get_tickers()

    for target_date in _date_list:
        logging.info(f"Processing date {target_date}")
        missing = set(all_syms) - get_existing(target_date)
        if not missing:
            continue

        rows = []
        with ThreadPoolExecutor(max_workers=8) as exe:
            futures = {exe.submit(fetch_symbol_data, s, target_date): s for s in missing}
            for fut in as_completed(futures):
                sym = futures[fut]
                try:
                    data = fut.result()
                    rows.append((
                        data['symbol'],
                        data['trade_date'],
                        data['open_price'],
                        data['high_price'],
                        data['low_price'],
                        data['close_price'],
                        data['volume'],
                    ))
                except Exception as e:
                    logging.error(f"{sym}@{target_date} failed: {e}")

        if rows:
            insert_daily_closes(rows)
            total += len(rows)

    return total

# allow direct execution for testing
if __name__ == '__main__':
    count = refresh_daily_closes()
    print(f"Upserted {count} rows into daily_closes.")
