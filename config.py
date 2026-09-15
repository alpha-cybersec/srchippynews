from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent

DATA_DIR = PROJECT_ROOT / "data"
FEEDS_DIR = DATA_DIR / "feeds"
HISTORY_DIR = DATA_DIR / "history"
DAILY_DIR = DATA_DIR / "daily"
ALLNEWS_FILE = DATA_DIR / "allnews.json"

TIMEZONE_NAME = "America/Guayaquil"

REQUEST_TIMEOUT_SECONDS = 30

DAILY_RETENTION_DAYS = 30
HISTORY_RETENTION_MONTHS = 12


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 "
        "Chrome/140.0 Safari/537.36 "
        "CTI-Chippy-News/3.0"
    ),
    "Accept": (
        "application/rss+xml,"
        "application/atom+xml;q=0.9,"
        "application/xml;q=0.9,"
        "text/xml;q=0.8,"
        "*/*;q=0.5"
    ),
}
