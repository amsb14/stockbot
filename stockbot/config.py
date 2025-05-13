import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY")
TAP_SECRET_KEY = os.getenv("TAP_SECRET_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")

PG_DB = os.getenv("PG_DB")
PG_USER = os.getenv("PG_USER")
PG_PASS = os.getenv("PG_PASS")
PG_HOST = os.getenv("PG_HOST")
PG_PORT = os.getenv("PG_PORT")

# Rate limit configuration
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_CALLS = 5  # max calls per window

# adjust path as needed
COMPANIES_PATH = Path(__file__).parent.parent / "data" / "companies.txt"
raw = COMPANIES_PATH.read_text(encoding="utf-8").splitlines()

COMPANIES = []
for line in raw:
    line = line.strip()
    # skip empty lines or lines starting with #
    if not line or line.startswith("#"):
        continue
    COMPANIES.append(line)