import logging
from datetime import datetime
import yfinance as yf
from psycopg2.extras import execute_values
from stockbot.database.connection import get_db_conn, put_db_conn
from stockbot.data import COMPANIES

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

# ─── Fetch Income Statements ────────────────────────────────────────────────────

def get_income_statements(symbols):
    rows = []
    for sym in symbols:
        try:
            stock = yf.Ticker(sym)
            for freq, label in [("yearly", "Annual"), ("quarterly", "Quarterly")]:
                df = stock.get_income_stmt(freq=freq)
                if df is None or df.empty:
                    continue
                for dt in df.columns:
                    data = df[dt].to_dict()
                    # extract selected metrics, default to 0
                    values = [data.get(key) or 0 for key in METRIC_KEYS]
                    # row: ticker, statement_type, fiscal_date, *metrics, updated_date
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

# ─── Insert Income Statements into PostgreSQL ─────────────────────────────────

def insert_income_statements(rows):
    # build quoted column list for SQL
    pk_cols = ['"Ticker"', '"Statement_Type"', '"Fiscal_Date"']
    data_cols = [f'"{col}"' for col in METRIC_KEYS]
    all_cols = [pk_cols[0], pk_cols[1], pk_cols[2]] + data_cols + ['"Updated_Date"']
    col_list = ", ".join(all_cols)
    # conflict target uses unquoted columns (Postgres folds to lowercase, but quoting ensures case awareness)
    conflict = '"Ticker", "Statement_Type", "Fiscal_Date"'
    # build SET assignments excluding PKs
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
            execute_values(cur, sql, rows)
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
