# stockbot/data/__init__.py
import pkgutil
import io
import csv

# # read the raw file bundled with this package
# raw = pkgutil.get_data(__name__, "companies.txt").decode("utf-8").splitlines()
#
# # strip out blanks & comments
# COMPANIES = [
#     line.strip()
#     for line in raw
#     if line.strip() and not line.strip().startswith("#")
# ]


# Load the raw CSV bundled with this package
raw = pkgutil.get_data(__name__, "companies.csv")
if raw is None:
    raise RuntimeError("companies.csv not found in package data")

# Decode and parse CSV
text = raw.decode("utf-8")
reader = csv.reader(io.StringIO(text))

# If your CSV has a header row, skip it:
header = next(reader, None)

# Extract the first column (Ticker) from each subsequent row
COMPANIES = [
    row[0].strip()
    for row in reader
    if row and row[0].strip() and not row[0].startswith("#")
]