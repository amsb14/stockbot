import logging
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import pytz
import pandas as pd
import yfinance as yf
from psycopg2.extras import execute_values

from stockbot.database.connection import get_db_conn, put_db_conn
from stockbot.data import COMPANIES

# ─────────── Assess Dividend Continuity ───────────
def assess_dividend_continuity(hist_dividends):
    prev, yrs, incs = 0, 0, 0
    for d in hist_dividends:
        if d > 0:
            yrs += 1
            if d > prev:
                incs += 1
        prev = d
    if yrs == len(hist_dividends) and incs > 0:
        return "High"
    if yrs == len(hist_dividends):
        return "Moderate"
    return "Low"

# ─────────── Fetch stock info using yfinance ───────────
def fetch_symbol_info(symbol):
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        divs = stock.dividends

        # Defaults
        last_div_value = None
        last_div_date = None
        continuity = "N/A"

        # Dividend analysis
        if not divs.empty:
            five_years_ago = (datetime.utcnow() - timedelta(days=365 * 5)).replace(tzinfo=pytz.UTC)
            divs_filtered = divs[five_years_ago:]
            if not divs_filtered.empty and isinstance(divs_filtered.index, pd.DatetimeIndex):
                yearly_sums = divs_filtered.groupby(pd.Grouper(freq='Y')).sum()
                continuity = assess_dividend_continuity(yearly_sums)

            last_div_value = float(divs.iloc[-1])
            last_div_date = divs.index[-1].date()

    except Exception as e:
        logging.warning(f"Error fetching info for {symbol}: {e}")
        return None

    return (
        symbol,
        info.get('exchange'),
        info.get('industry'),
        info.get('sector'),
        info.get('currentPrice'),
        info.get('address1'),
        info.get('city'),
        info.get('zip'),
        info.get('country'),
        info.get('phone'),
        info.get('fax'),
        info.get('website'),
        info.get('longBusinessSummary'),
        info.get('previousClose'),
        info.get('open'),
        info.get('dayLow'),
        info.get('dayHigh'),
        info.get('dividendYield'),
        info.get('exDividendDate'),
        info.get('fiveYearAvgDividendYield'),
        info.get('trailingPE'),
        info.get('volume'),
        info.get('marketCap'),
        info.get('fiftyTwoWeekLow'),
        info.get('fiftyTwoWeekHigh'),
        info.get('fiftyDayAverage'),
        info.get('twoHundredDayAverage'),
        info.get('sharesOutstanding'),
        info.get('bookValue'),
        info.get('priceToBook'),
        last_div_value,
        str(last_div_date) if last_div_date else None,
        info.get('recommendationKey'),
        info.get('totalCash'),
        info.get('ebitda'),
        info.get('totalDebt'),
        info.get('currentRatio'),
        info.get('totalRevenue'),
        info.get('returnOnAssets'),
        info.get('returnOnEquity'),
        info.get('financialCurrency'),
        info.get('marketState'),
        info.get('averageDailyVolume3Month'),
        info.get('fiftyTwoWeekLowChangePercent'),
        info.get('fiftyTwoWeekHighChangePercent'),
        continuity,
        datetime.utcnow().date()
    )

# ─────────── Insert/Upsert stock info into PostgreSQL ───────────
def insert_stock_info(rows):
    conn = get_db_conn()
    sql = """
    INSERT INTO stock_data (
        symbol, exchange, industry, sector, "currentPrice",
        address1, city, zip, country, phone, fax, website,
        "longBusinessSummary", "previousClose", "open", "dayLow",
        "dayHigh", "dividendYield", "exDividendDate",
        "fiveYearAvgDividendYield", "trailingPE", "volume",
        "marketCap", "fiftyTwoWeekLow", "fiftyTwoWeekHigh",
        "fiftyDayAverage", "twoHundredDayAverage",
        "sharesOutstanding", "bookValue", "priceToBook",
        "lastDividendValue", "lastDividendDate",
        "recommendationKey", "totalCash", "ebitda",
        "totalDebt", "currentRatio", "totalRevenue",
        "returnOnAssets", "returnOnEquity",
        "financialCurrency", "marketState",
        "averageDailyVolume3Month",
        "fiftyTwoWeekLowChangePercent",
        "fiftyTwoWeekHighChangePercent",
        "dividendContinuity", updated_date
    ) VALUES %s
    ON CONFLICT (symbol) DO UPDATE SET
        exchange = EXCLUDED.exchange,
        industry = EXCLUDED.industry,
        sector = EXCLUDED.sector,
        "currentPrice" = EXCLUDED."currentPrice",
        address1 = EXCLUDED.address1,
        city = EXCLUDED.city,
        zip = EXCLUDED.zip,
        country = EXCLUDED.country,
        phone = EXCLUDED.phone,
        fax = EXCLUDED.fax,
        website = EXCLUDED.website,
        "longBusinessSummary" = EXCLUDED."longBusinessSummary",
        "previousClose" = EXCLUDED."previousClose",
        "open" = EXCLUDED."open",
        "dayLow" = EXCLUDED."dayLow",
        "dayHigh" = EXCLUDED."dayHigh",
        "dividendYield" = EXCLUDED."dividendYield",
        "exDividendDate" = EXCLUDED."exDividendDate",
        "fiveYearAvgDividendYield" = EXCLUDED."fiveYearAvgDividendYield",
        "trailingPE" = EXCLUDED."trailingPE",
        "volume" = EXCLUDED."volume",
        "marketCap" = EXCLUDED."marketCap",
        "fiftyTwoWeekLow" = EXCLUDED."fiftyTwoWeekLow",
        "fiftyTwoWeekHigh" = EXCLUDED."fiftyTwoWeekHigh",
        "fiftyDayAverage" = EXCLUDED."fiftyDayAverage",
        "twoHundredDayAverage" = EXCLUDED."twoHundredDayAverage",
        "sharesOutstanding" = EXCLUDED."sharesOutstanding",
        "bookValue" = EXCLUDED."bookValue",
        "priceToBook" = EXCLUDED."priceToBook",
        "lastDividendValue" = EXCLUDED."lastDividendValue",
        "lastDividendDate" = EXCLUDED."lastDividendDate",
        "recommendationKey" = EXCLUDED."recommendationKey",
        "totalCash" = EXCLUDED."totalCash",
        "ebitda" = EXCLUDED."ebitda",
        "totalDebt" = EXCLUDED."totalDebt",
        "currentRatio" = EXCLUDED."currentRatio",
        "totalRevenue" = EXCLUDED."totalRevenue",
        "returnOnAssets" = EXCLUDED."returnOnAssets",
        "returnOnEquity" = EXCLUDED."returnOnEquity",
        "financialCurrency" = EXCLUDED."financialCurrency",
        "marketState" = EXCLUDED."marketState",
        "averageDailyVolume3Month" = EXCLUDED."averageDailyVolume3Month",
        "fiftyTwoWeekLowChangePercent" = EXCLUDED."fiftyTwoWeekLowChangePercent",
        "fiftyTwoWeekHighChangePercent" = EXCLUDED."fiftyTwoWeekHighChangePercent",
        "dividendContinuity" = EXCLUDED."dividendContinuity",
        updated_date = EXCLUDED.updated_date;
    """
    try:
        with conn.cursor() as cur:
            execute_values(cur, sql, rows)
        conn.commit()
    except Exception as e:
        logging.error(f"Error inserting stock info: {e}")
        conn.rollback()
    finally:
        put_db_conn(conn)

# ─────────── ETL: multithreaded fetch and load ───────────
def etl_stock_info(symbols):
    with ThreadPoolExecutor(max_workers=5) as exe:
        results = exe.map(fetch_symbol_info, symbols)
        rows = [r for r in results if r]
    if not rows:
        logging.info("No stock info to insert.")
        return 0
    insert_stock_info(rows)
    return len(rows)

# ─────────── Manual refresh wrapper ───────────
def refresh_stockinfo_test():
    count = etl_stock_info(COMPANIES)
    logging.info(f"Processed {count} stock_info records.")
    return count
