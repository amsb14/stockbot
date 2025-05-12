import logging
from datetime import datetime
import yfinance as yf
from psycopg2.extras import execute_values
from stockbot.database.connection import get_db_conn, put_db_conn
import sys
sys.stdout.reconfigure(line_buffering=True)

# ─── Test Universe ─────────────────────────────────────────────────────────────
COMPANIES = ["GOOG"]  # adjust or import from config as needed

# ─── Fetch Cashflow Data from YFinance ─────────────────────────────────────────
def get_cashflows():
    ticker = yf.Ticker("GOOG")
    df_yearly    = ticker.get_cash_flow(freq="yearly")
    df_quarterly = ticker.get_cash_flow(freq="quarterly")

    print("Yearly cash-flow DF:\n", df_yearly)
    print("– index (metrics):", df_yearly.index.tolist())
    print("– columns (dates):", df_yearly.columns.tolist(), "\n")

    print("Quarterly cash-flow DF:\n", df_quarterly)
    print("– index:", df_quarterly.index.tolist())
    print("– columns:", df_quarterly.columns.tolist())

# ─── Insert Data into PostgreSQL ────────────────────────────────────────────────
def insert_cashflows(rows):
    sql = """
    INSERT INTO cash_flows (
        ticker,
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
    )
    VALUES %s
    ON CONFLICT (ticker, "Statement_Type", fiscal_date) DO UPDATE SET
        "OperatingCashFlow"            = EXCLUDED."OperatingCashFlow",
        "FreeCashFlow"                 = EXCLUDED."FreeCashFlow",
        "InvestingCashFlow"            = EXCLUDED."InvestingCashFlow",
        "FinancingCashFlow"            = EXCLUDED."FinancingCashFlow",
        "CapitalExpenditure"           = EXCLUDED."CapitalExpenditure",
        "ChangesInCash"                = EXCLUDED."ChangesInCash",
        "DepreciationAndAmortization"  = EXCLUDED."DepreciationAndAmortization",
        "CashDividendsPaid"            = EXCLUDED."CashDividendsPaid",
        updated_date                   = EXCLUDED.updated_date;
    """
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            execute_values(cur, sql, rows)
        # If autocommit is disabled, you can uncomment the next line:
        # conn.commit()
    finally:
        put_db_conn(conn)

# ─── Orchestration Function ─────────────────────────────────────────────────────
def refresh_cashflow_test():
    """
    Fetch & upsert cashflow_test on demand.
    Returns the number of rows processed.
    """
    get_cashflows()
    # if not rows:
    #     return 0
    # insert_cashflows(rows)
    # return len(rows)
