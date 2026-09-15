from config import FEEDS_DIR
from rss_common import collect_source

SOURCE_NAME = "Cyber Security News"
SOURCE_SLUG = "cybersecuritynews"

FEEDS = [
    {"key": "ORIGINAL", "label": "CyberSecurityNews-ORIGINAL", "url": "https://cybersecuritynews.com/feed/"},
    {"key": "FEEDBURNER", "label": "CyberSecurityNews-FEEDBURNER", "url": "https://feeds.feedburner.com/cyber-security-news"},
]

SNAPSHOT_FILE = FEEDS_DIR / "cybersecuritynews.json"


def collect():
    return collect_source(SOURCE_NAME, SOURCE_SLUG, FEEDS, SNAPSHOT_FILE)


if __name__ == "__main__":
    collect()
