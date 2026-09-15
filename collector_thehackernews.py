from config import FEEDS_DIR
from rss_common import collect_source

SOURCE_NAME = "The Hacker News"
SOURCE_SLUG = "thehackernews"

FEEDS = [
    {
        "key": "ORIGINAL",
        "label": "TheHackerNews-ORIGINAL",
        "url": "https://thehackernews.com/feeds/posts/default?alt=rss&redirect=false",
    },
    {
        "key": "FEEDBURNER",
        "label": "TheHackerNews-FEEDBURNER",
        "url": "https://feeds.feedburner.com/TheHackersNews",
    },
]

SNAPSHOT_FILE = FEEDS_DIR / "thehackernews.json"


def collect():
    return collect_source(SOURCE_NAME, SOURCE_SLUG, FEEDS, SNAPSHOT_FILE)


if __name__ == "__main__":
    collect()
