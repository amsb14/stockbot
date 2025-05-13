import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import yfinance as yf
from psycopg2.extras import execute_values

from stockbot.database.connection import get_db_conn, put_db_conn
from stockbot.data import COMPANIES


# ─── Selected Balance Sheet Metrics ────────────────────────────────────────────
METRIC_KEYS = [
    "OrdinarySharesNumber",
    "ShareIssued",
    "TangibleBookValue",
    "InvestedCapital",
    "WorkingCapital",
    "NetTangibleAssets",
    "CommonStockEquity",
    "TotalCapitalization",
    "TotalEquityGrossMinorityInterest",
    "StockholdersEquity",
    "RetainedEarnings",
    "CapitalStock",
    "CommonStock",
    "TotalLiabilitiesNetMinorityInterest",
    "TotalNonCurrentLiabilitiesNetMinorityInterest",
    "CurrentLiabilities",
    "Payables",
    "TotalAssets",
    "TotalNonCurrentAssets",
    "GoodwillAndOtherIntangibleAssets",
    "NetPPE",
    "CurrentAssets",
    "OtherCurrentAssets",
    "CashCashEquivalentsAndShortTermInvestments",
    "CashAndCashEquivalents",
    "TotalDebt",
    "CapitalLeaseObligations",
    "LongTermDebtAndCapitalLeaseObligation",
    "LongTermCapitalLeaseObligation",
    "CurrentDebtAndCapitalLeaseObligation",
    "GrossPPE",
    "OtherProperties",
    "OtherShortTermInvestments",
    "LongTermDebt",
    "TotalTaxPayable",
    "AccountsPayable",
    "AccumulatedDepreciation",
    "Properties",
    "Inventory",
    "AccountsReceivable"
]

# ─── Fetch Balance Sheets ──────────────────────────────────────────────────────
def fetch_balance_for_symbol(sym):
    rows = []
    try:
        stock = yf.Ticker(sym)
        for freq, label in [("yearly", "Annual"), ("quarterly", "Quarterly")]:
            df = stock.get_balance_sheet(freq=freq)
            if df is None or df.empty:
                continue
            for dt in df.columns:
                data = df[dt].to_dict()
                # extract metrics in METRIC_KEYS order
                values = [data.get(key) or 0 for key in METRIC_KEYS]
                row = (
                    sym,
                    label,
                    dt.strftime("%Y-%m-%d"),
                    *values,
                    datetime.utcnow().strftime("%Y-%m-%d")
                )
                rows.append(row)
    except Exception as e:
        logging.warning(f"Error fetching balance sheet for {sym}: {e}")
    return rows

# ─── Fetch all balance-sheets in parallel ───────────────────────────────────────
def get_balance_sheets(symbols):
    all_rows = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_map = {executor.submit(fetch_balance_for_symbol, s): s for s in symbols}
        for fut in as_completed(future_map):
            sym = future_map[fut]
            try:
                result = fut.result()
                if result:
                    all_rows.extend(result)
            except Exception as e:
                logging.warning(f"Failed balance sheet for {sym}: {e}")
    return all_rows

# ─── Insert Data into PostgreSQL with Deduplication ─────────────────────────────

def insert_balance_sheets(rows):
    # Deduplicate by primary key (Ticker, Statement_Type, Fiscal_Date)
    unique = {}
    for row in rows:
        pk = (row[0], row[1], row[2])
        unique[pk] = row
    deduped_rows = list(unique.values())

    # quote column names
    pk_cols = ['"Ticker"', '"Statement_Type"', '"Fiscal_Date"']
    data_cols = [f'"{col}"' for col in METRIC_KEYS]
    all_cols = pk_cols + data_cols + ['"Updated_Date"']
    col_list = ", ".join(all_cols)
    conflict = '"Ticker", "Statement_Type", "Fiscal_Date"'
    assignments = ",\n        ".join(
        f"{col} = EXCLUDED.{col}" for col in all_cols if col not in pk_cols
    )

    sql = f"""
    INSERT INTO balance_sheets (
        {col_list}
    ) VALUES %s
    ON CONFLICT ({conflict}) DO UPDATE SET
        {assignments}
    ;
    """

    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            execute_values(cur, sql, deduped_rows)
    finally:
        put_db_conn(conn)

# ─── Orchestration Function ─────────────────────────────────────────────────────

def refresh_balance_test():
    """
    Fetch & upsert balance_sheets on demand.
    Returns the number of rows processed.
    """
    rows = get_balance_sheets(COMPANIES)
    if not rows:
        return 0
    insert_balance_sheets(rows)
    return len(rows)

