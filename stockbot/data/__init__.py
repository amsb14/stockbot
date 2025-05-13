# stockbot/data/__init__.py
import pkgutil

# read the raw file bundled with this package
raw = pkgutil.get_data(__name__, "companies.txt").decode("utf-8").splitlines()

# strip out blanks & comments
COMPANIES = [
    line.strip()
    for line in raw
    if line.strip() and not line.strip().startswith("#")
]