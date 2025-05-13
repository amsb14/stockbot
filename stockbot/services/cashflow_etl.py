import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import yfinance as yf
from psycopg2.extras import execute_values

from stockbot.database.connection import get_db_conn, put_db_conn
from stockbot.data import COMPANIES

# ─── Per-symbol fetch to enable parallel execution ──────────────────────────────
def fetch_cashflows_for_symbol(sym):
    rows = []
    try:
        stock = yf.Ticker(sym)
        for freq, label in [("yearly", "Annual"), ("quarterly", "Quarterly")]:
            df = stock.get_cash_flow(freq=freq)
            if df is None or df.empty:
                continue
            for dt in df.columns:
                data = df[dt].to_dict()
                rows.append((
                    sym,
                    label,
                    dt.strftime("%Y-%m-%d"),
                    data.get("OperatingCashFlow")             or 0,
                    data.get("FreeCashFlow")                  or 0,
                    data.get("InvestingCashFlow")             or 0,
                    data.get("FinancingCashFlow")             or 0,
                    data.get("CapitalExpenditure")            or 0,
                    data.get("ChangesInCash")                 or 0,
                    data.get("DepreciationAndAmortization")   or 0,
                    data.get("CashDividendsPaid")             or 0,
                    datetime.utcnow().strftime("%Y-%m-%d")
                ))
    except Exception as e:
        logging.warning(f"Error fetching cash flow for {sym}: {e}")
    return rows

# ─── Fetch all cash-flows in parallel ───────────────────────────────────────────
def get_cashflows(symbols):
    all_rows = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_map = {executor.submit(fetch_cashflows_for_symbol, s): s for s in symbols}
        for fut in as_completed(future_map):
            sym = future_map[fut]
            try:
                result = fut.result()
                if result:
                    all_rows.extend(result)
            except Exception as e:
                logging.warning(f"Failed cash-flow for {sym}: {e}")
    return all_rows

# ─── Insert Data into PostgreSQL with Deduplication ──────────────────────────────
def insert_cashflows(rows):
    # Deduplicate by primary key (ticker, Statement_Type, fiscal_date)
    unique = {}
    for row in rows:
        pk = (row[0], row[1], row[2])
        unique[pk] = row
    deduped_rows = list(unique.values())

    sql = """
    INSERT INTO cash_flows (
        "Ticker",
        "Statement_Type",
        fiscal_date,
        "OperatingCashFlow",
        "FreeCashFlow",
        "InvestingCashFlow",
        "FinancingCashFlow",
        "CapitalExpenditure",
        "ChangesInCash",
        "DepreciationAndAmortization",
        "CashDividendsPaid",
        updated_date
    ) VALUES %s
    ON CONFLICT ("Ticker", "Statement_Type", fiscal_date) DO UPDATE SET
        "OperatingCashFlow"           = EXCLUDED."OperatingCashFlow",
        "FreeCashFlow"                = EXCLUDED."FreeCashFlow",
        "InvestingCashFlow"           = EXCLUDED."InvestingCashFlow",
        "FinancingCashFlow"           = EXCLUDED."FinancingCashFlow",
        "CapitalExpenditure"          = EXCLUDED."CapitalExpenditure",
        "ChangesInCash"               = EXCLUDED."ChangesInCash",
        "DepreciationAndAmortization" = EXCLUDED."DepreciationAndAmortization",
        "CashDividendsPaid"           = EXCLUDED."CashDividendsPaid",
        updated_date                  = EXCLUDED.updated_date;
    """

    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            execute_values(cur, sql, deduped_rows)
    finally:
        put_db_conn(conn)

# ─── Orchestration Function ─────────────────────────────────────────────────────
def refresh_cashflow_test():
    """
    Fetch & upsert cash_flows on demand.
    Returns the number of rows processed.
    """
    rows = get_cashflows(COMPANIES)
    if not rows:
        return 0
    insert_cashflows(rows)
    return len(rows)
