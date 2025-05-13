import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import yfinance as yf
from psycopg2.extras import execute_values

from stockbot.database.connection import get_db_conn, put_db_conn
from stockbot.config import COMPANIES

# ─── Selected Income Statement Metrics ─────────────────────────────────────────
METRIC_KEYS = [
    "TaxEffectOfUnusualItems",
    "TaxRateForCalcs",
    "NormalizedEBITDA",
    "NetIncomeFromContinuingOperationNetMinorityInterest",
    "ReconciledDepreciation",
    "ReconciledCostOfRevenue",
    "EBITDA",
    "EBIT",
    "NetInterestIncome",
    "InterestExpense",
    "InterestIncome",
    "NormalizedIncome",
    "NetIncomeFromContinuingAndDiscontinuedOperation",
    "TotalExpenses",
    "TotalOperatingIncomeAsReported",
    "DilutedAverageShares",
    "BasicAverageShares",
    "DilutedEPS",
    "BasicEPS",
    "DilutedNIAvailtoComStockholders",
    "NetIncomeCommonStockholders",
    "NetIncome",
    "NetIncomeIncludingNoncontrollingInterests",
    "NetIncomeContinuousOperations",
    "TaxProvision",
    "PretaxIncome",
    "OtherIncomeExpense",
    "OtherNonOperatingIncomeExpenses",
    "NetNonOperatingInterestIncomeExpense",
    "InterestExpenseNonOperating",
    "InterestIncomeNonOperating",
    "OperatingIncome",
    "OperatingExpense",
    "ResearchAndDevelopment",
    "SellingGeneralAndAdministration",
    "GrossProfit",
    "CostOfRevenue",
    "TotalRevenue",
    "OperatingRevenue",
    "TotalUnusualItems",
    "TotalUnusualItemsExcludingGoodwill",
    "SpecialIncomeCharges",
    "WriteOff",
    "GainOnSaleOfSecurity",
    "SellingAndMarketingExpense",
    "GeneralAndAdministrativeExpense",
    "OtherGandA",
    "RentExpenseSupplemental",
    "AverageDilutionEarnings",
    "OtherunderPreferredStockDividend",
    "MinorityInterests",
    "RestructuringAndMergernAcquisition"
]

# ─── Per-symbol fetch to enable parallel execution ──────────────────────────────
def fetch_income_for_symbol(sym):
    rows = []
    try:
        stock = yf.Ticker(sym)
        for freq, label in [("yearly", "Annual"), ("quarterly", "Quarterly")]:
            df = stock.get_income_stmt(freq=freq)
            if df is None or df.empty:
                continue
            for dt in df.columns:
                data = df[dt].to_dict()
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
        logging.warning(f"Error fetching income statement for {sym}: {e}")
    return rows

# ─── Fetch all income statements in parallel ───────────────────────────────────
def get_income_statements(symbols):
    all_rows = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_map = {executor.submit(fetch_income_for_symbol, s): s for s in symbols}
        for fut in as_completed(future_map):
            sym = future_map[fut]
            try:
                result = fut.result()
                if result:
                    all_rows.extend(result)
            except Exception as e:
                logging.warning(f"Failed income statement for {sym}: {e}")
    return all_rows

# ─── Insert Income Statements into PostgreSQL with Deduplication ───────────────
def insert_income_statements(rows):
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
    INSERT INTO income_statements (
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
def refresh_income_test():
    """
    Fetch & upsert income_statements on demand.
    Returns the number of rows processed.
    """
    rows = get_income_statements(COMPANIES)
    if not rows:
        return 0
    insert_income_statements(rows)
    return len(rows)
