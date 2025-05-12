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
def get_cashflows(symbols):
    rows = []
    for sym in symbols:
        try:
            stock = yf.Ticker(sym)
            for freq, label in [("yearly", "Annual"), ("quarterly", "Quarterly")]:
                df = stock.get_cash_flow(freq=freq)
                print(df, flush=True)  # Do you see a DataFrame with rows?
                print(df.columns)  # Check which dates you get
                print(df.index.tolist())  # See the exact metric names
                if df is None or df.empty:
                    continue

                for dt in df.columns:
                    data = df[dt].to_dict()
                    ocf     = data.get("OperatingCashFlow")             or 0
                    fcf     = data.get("FreeCashFlow")                  or 0
                    icf     = data.get("InvestingCashFlow")             or 0
                    fincf   = data.get("FinancingCashFlow")             or 0
                    capex   = data.get("CapitalExpenditure")            or 0
                    chg_cash= data.get("ChangesInCash")                 or 0
                    d_and_a = data.get("DepreciationAndAmortization")   or 0
                    div_paid= data.get("CashDividendsPaid")             or 0

                    rows.append((
                        sym,
                        label,
                        dt.strftime("%Y-%m-%d"),
                        ocf,
                        fcf,
                        icf,
                        fincf,
                        capex,
                        chg_cash,
                        d_and_a,
                        div_paid,
                        datetime.utcnow().strftime("%Y-%m-%d")
                    ))
        except Exception as e:
            logging.warning(f"Error fetching cash flow for {sym}: {e}")
    return rows

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
    rows = get_cashflows(COMPANIES)
    if not rows:
        return 0
    insert_cashflows(rows)
    return len(rows)
