# File: stockbot/services/shariah_etl.py

import requests
import pandas as pd
from bs4 import BeautifulSoup
from psycopg2.extras import execute_values
from stockbot.database.connection import get_db_conn, put_db_conn


def scrape_shariah_data():
    """
    Scrape Shariah compliance data from Argaam and return a DataFrame.
    Columns: stock, al_rajhi, dr_mohammed_bin_saud_al_osaimi, al_inma, al_bilad
    """
    url = "https://www.argaam.com/ar/company/shariahcompanies"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, "lxml")
    table = soup.find("table")
    rows = table.find_all("tr")[1:]
    data = []

    for row in rows:
        if row.find("td", {"colspan": "9"}):
            continue
        symbol = row.find("td", class_="stock-symbol").get_text(strip=True)
        checks = row.find_all("td", class_="center")[:4]
        status = ["✔" in check.get_text() for check in checks]
        data.append([f"{symbol}.SR"] + status)

    df = pd.DataFrame(data, columns=[
        "stock",
        "al_rajhi",
        "dr_mohammed_bin_saud_al_osaimi",
        "al_inma",
        "al_bilad"
    ])
    return df


def update_shariah_table():
    """
    Fetch Shariah compliance data and upsert into the database table `shariah_compliance`.
    Returns the number of rows processed.
    """
    df = scrape_shariah_data()
    conn = get_db_conn()
    cur = conn.cursor()

    # Convert DataFrame rows to plain Python tuples to avoid numpy types
    values = [
        (
            row['stock'],
            bool(row['al_rajhi']),
            bool(row['dr_mohammed_bin_saud_al_osaimi']),
            bool(row['al_inma']),
            bool(row['al_bilad'])
        )
        for _, row in df.iterrows()
    ]

    query = """
        INSERT INTO shariah_compliance (
            stock,
            al_rajhi,
            dr_mohammed_bin_saud_al_osaimi,
            al_inma,
            al_bilad
        ) VALUES %s
        ON CONFLICT (stock) DO UPDATE SET
            al_rajhi = EXCLUDED.al_rajhi,
            dr_mohammed_bin_saud_al_osaimi = EXCLUDED.dr_mohammed_bin_saud_al_osaimi,
            al_inma = EXCLUDED.al_inma,
            al_bilad = EXCLUDED.al_bilad;
    """

    execute_values(cur, query, values)
    conn.commit()
    cur.close()
    put_db_conn(conn)
    return len(values)
