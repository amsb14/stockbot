import re
from rapidfuzz import process, fuzz
from stockbot.database.connection import get_db_conn, put_db_conn

TICKER_DATA = []
AR_NAMES = []
EN_NAMES = []

def _normalize_ar(txt: str) -> str:
    pat = re.compile(r"[\u0617-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")
    txt = pat.sub("", txt)
    txt = txt.replace("ـ", "")
    txt = txt.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt

def _normalize_en(txt: str) -> str:
    return re.sub(r"\s+", " ", txt.lower().strip())

def _detect_lang(txt: str) -> str:
    return 'arabic' if re.search(r'[\u0600-\u06FF]', txt) else 'english'

def load_ticker_names():
    global TICKER_DATA, AR_NAMES, EN_NAMES
    conn = get_db_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT symbol, arabic_name, english_name FROM tickers_ar_en;")
        TICKER_DATA = cur.fetchall()
    put_db_conn(conn)

    AR_NAMES = [row[1] for row in TICKER_DATA if row[1]]
    EN_NAMES = [row[2] for row in TICKER_DATA if row[2]]

def parse_symbol(raw: str):
    s = raw.strip().upper()
    m = re.fullmatch(r'(\d{4})(\.SR)?', s)
    if m:
        base = m.group(1)
        return f"{base}.SR", base, True
    return s, s, False

def symbol_exists_in_db(sym: str) -> bool:
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM tickers_ar_en WHERE symbol = %s LIMIT 1;", (sym,))
            return cur.fetchone() is not None
    finally:
        put_db_conn(conn)

def find_top_matches(query: str, max_results: int = 5, min_score: int = 60):
    lang = _detect_lang(query)
    q_norm = _normalize_ar(query) if lang == 'arabic' else _normalize_en(query)

    norm_ar = {_normalize_ar(row[1]): row for row in TICKER_DATA if row[1]}
    norm_en = {_normalize_en(row[2]): row for row in TICKER_DATA if row[2]}

    ar_matches = process.extract(q_norm, list(norm_ar.keys()), scorer=fuzz.WRatio, limit=max_results)
    en_matches = process.extract(q_norm, list(norm_en.keys()), scorer=fuzz.WRatio, limit=max_results)

    results = []
    for txt, score, _ in ar_matches + en_matches:
        if score < min_score:
            continue
        row = norm_ar.get(txt) or norm_en.get(txt)
        results.append((row[0], row[1] or row[2], score))

    seen, final = set(), []
    for sym, name, sc in sorted(results, key=lambda x: x[2], reverse=True):
        if sym not in seen:
            final.append((sym, name, sc))
            seen.add(sym)
        if len(final) == max_results:
            break
    return final

# Load ticker names on module import
load_ticker_names()
