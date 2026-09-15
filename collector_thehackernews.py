from datetime import datetime
from zoneinfo import ZoneInfo

from config import FEEDS_DIR
from rss_common import collect_source, atomic_write_json


SOURCE_NAME = "The Hacker News"
SOURCE_SLUG = "thehackernews"

TIMEZONE_NAME = "America/Guayaquil"
LOCAL_TZ = ZoneInfo(TIMEZONE_NAME)

FEEDS = [
    {
        "key": "ORIGINAL",
        "label": "TheHackerNews-ORIGINAL",
        "url": (
            "https://thehackernews.com/feeds/posts/default"
            "?alt=rss&redirect=false"
        ),
    },
    {
        "key": "FEEDBURNER",
        "label": "TheHackerNews-FEEDBURNER",
        "url": "https://feeds.feedburner.com/TheHackersNews",
    },
]

SNAPSHOT_FILE = FEEDS_DIR / "thehackernews.json"


def is_today(article):
    """
    Devuelve True solamente si la fecha de publicación
    corresponde al día actual en America/Guayaquil.
    """

    published_utc = article.get("published_utc", "")

    if not published_utc:
        return False

    try:
        published_dt = datetime.fromisoformat(published_utc)

        published_local = published_dt.astimezone(LOCAL_TZ)

        today_local = datetime.now(LOCAL_TZ).date()

        return published_local.date() == today_local

    except Exception as exc:
        print(
            f"[WARNING] No se pudo validar fecha: "
            f"{article.get('title', '')}"
        )
        print(f"[WARNING] Error: {exc}")

        return False


def filter_today(snapshot):
    """
    Filtra ORIGINAL y FEEDBURNER dejando únicamente
    artículos publicados hoy.
    """

    results = snapshot.get("results", {})

    print("")
    print("=" * 88)
    print("THE HACKER NEWS - FILTRO DEL DIA")
    print("=" * 88)

    for endpoint_name in ("ORIGINAL", "FEEDBURNER"):

        endpoint = results.get(endpoint_name)

        if not endpoint:
            continue

        articles_before = endpoint.get("articles", [])

        articles_today = [
            article
            for article in articles_before
            if is_today(article)
        ]

        print(
            f"[{endpoint_name}] "
            f"RSS recibido: {len(articles_before)}"
        )

        print(
            f"[{endpoint_name}] "
            f"Noticias de hoy: {len(articles_today)}"
        )

        endpoint["articles"] = articles_today
        endpoint["article_count"] = len(articles_today)

    return snapshot


def collect():

    snapshot = collect_source(
        source_name=SOURCE_NAME,
        source_slug=SOURCE_SLUG,
        feeds=FEEDS,
        snapshot_file=SNAPSHOT_FILE,
    )

    # Filtrar únicamente publicaciones del día actual.
    snapshot = filter_today(snapshot)

    # Sobrescribir snapshot con los resultados ya filtrados.
    atomic_write_json(
        SNAPSHOT_FILE,
        snapshot,
    )

    return snapshot


if __name__ == "__main__":
    collect()
